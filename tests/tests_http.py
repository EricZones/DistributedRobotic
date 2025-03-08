import socket
import time
import statistics

HTTP_HOST = 'controller' # local = localhost || docker = controller
HTTP_PORT = 8080

# Functional tests

def send_http_request(request: str) -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HTTP_HOST, HTTP_PORT))
        s.sendall(request.encode('utf-8'))
        response = s.recv(4096)  # Puffersize for response
    return response.decode('utf-8')
    
def test_get_status():
    request = (
        "GET /status HTTP/1.1\r\n"
        f"Host: {HTTP_HOST}\r\n"
        "Connection: close\r\n"
        "\r\n"
    )
    response = send_http_request(request)
    assert "200 OK" in response, "GET /status did not work as expected"
    print("GET /status Test successful")

def test_get_captain():
    request = (
        "GET /captain HTTP/1.1\r\n"
        f"Host: {HTTP_HOST}\r\n"
        "Connection: close\r\n"
        "\r\n"
    )
    response = send_http_request(request)
    assert "200 OK" in response, "GET /captain did not work as expected"
    print("GET /captain Test successful")
    
def test_get_health():
    request = (
        "GET /health HTTP/1.1\r\n"
        f"Host: {HTTP_HOST}\r\n"
        "Connection: close\r\n"
        "\r\n"
    )
    response = send_http_request(request)
    assert "200 OK" in response, "GET /health did not work as expected"
    print("GET /health Test successful")

def test_post_electCaptain():
    request = (
        "POST /electCaptain HTTP/1.1\r\n"
        f"Host: {HTTP_HOST}\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: 0\r\n"  # Kein Payload
        "Connection: close\r\n"
        "\r\n"
    )
    response = send_http_request(request)
    assert "200 OK" in response or "400 Bad Request" in response, "POST /electCaptain did not work as expected"
    print("POST /electCaptain Test successful")


# Non-functional test

def measure_rtt():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HTTP_HOST, HTTP_PORT))
        request = "POST /electCaptain HTTP/1.1\r\nContent-Length: 5\r\n\r\nDummy"
        start_time = time.time()
        s.sendall(request.encode())
        response = s.recv(1024)
        end_time = time.time()
        rtt = end_time - start_time
        return rtt

if __name__ == "__main__":
    print("Starting non-functional test (RTT)...")
    rtts = [measure_rtt() for _ in range(100)]

    # Calculations
    average_rtt = sum(rtts) / len(rtts)
    min_rtt = min(rtts)
    max_rtt = max(rtts)
    median_rtt = statistics.median(rtts)
    variance_rtt = statistics.variance(rtts) if len(rtts) > 1 else 0
    std_dev_rtt = statistics.stdev(rtts) if len(rtts) > 1 else 0

    # Save results in file
    with open("tests_http_rtt.txt", "w") as f:
        f.write("RTT results:\n")
        f.write("\n".join(f"{rtt:.6f}" for rtt in rtts))
        f.write("\n\nStatistic evaluation:\n")
        f.write(f"Average RTT: {average_rtt:.6f} seconds\n")
        f.write(f"Minimum RTT: {min_rtt:.6f} seconds\n")
        f.write(f"Maximum RTT: {max_rtt:.6f} seconds\n")
        f.write(f"Median RTT: {median_rtt:.6f} seconds\n")
        f.write(f"Variance RTT: {variance_rtt:.6f} seconds\n")
        f.write(f"Standard deviation RTT: {std_dev_rtt:.6f} seconds\n")

    print("Non-functional test-results saved in 'tests_http_rtt.txt'")
    print("Starting functional tests...")
    
    test_get_status()
    test_get_captain()
    test_get_health()
    test_post_electCaptain()
    
    print("All tests executed")
