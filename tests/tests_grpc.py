import grpc
from src.proto import robot_service_pb2
from src.proto import robot_service_pb2_grpc
import time
import statistics

GRPC_HOST = "controller" # local = localhost || docker = controller
GRPC_PORT = 50051
id = -1

# Functional tests

def test_register_robot():
    channel = grpc.insecure_channel(f"{GRPC_HOST}:{GRPC_PORT}")
    stub = robot_service_pb2_grpc.RobotServiceStub(channel)
    
    response = stub.RegisterRobot(robot_service_pb2.RobotInfo(name = "TestRobot"))
    channel.close()
    
    assert response.id is not None, "Robot-Registration did not work as expected"
    global id
    id = response.id
    print("Robot-Registration Test successful")

def test_unregister_robot():
    channel = grpc.insecure_channel(f"{GRPC_HOST}:{GRPC_PORT}")
    stub = robot_service_pb2_grpc.RobotServiceStub(channel)
    
    global id
    response = stub.UnregisterRobot(robot_service_pb2.RobotData(id = id, name = "TestRobot"))
    channel.close()
    
    assert response.success, "Robot-Unregistration did not work as expected"
    print("Robot-Unregistration Test successful")


# Non-functional test

def measure_rtt():
    channel = grpc.insecure_channel(f"{GRPC_HOST}:{GRPC_PORT}")
    stub = robot_service_pb2_grpc.RobotServiceStub(channel)
    
    start_time = time.time()
    response = stub.GetRobots(robot_service_pb2.Empty())
    end_time = time.time()
    rtt = end_time - start_time
    
    channel.close()
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
    with open("tests_grpc_rtt.txt", "w") as f:
        f.write("RTT results:\n")
        f.write("\n".join(f"{rtt:.6f}" for rtt in rtts))
        f.write("\n\nStatistic evaluation:\n")
        f.write(f"Average RTT: {average_rtt:.6f} seconds\n")
        f.write(f"Minimum RTT: {min_rtt:.6f} seconds\n")
        f.write(f"Maximum RTT: {max_rtt:.6f} seconds\n")
        f.write(f"Median RTT: {median_rtt:.6f} seconds\n")
        f.write(f"Variance RTT: {variance_rtt:.6f} seconds\n")
        f.write(f"Standard deviation RTT: {std_dev_rtt:.6f} seconds\n")

    print("Non-functional test-results saved in 'tests_grpc_rtt.txt'")
    
    print("Starting functional tests...")
    test_register_robot()
    test_unregister_robot()
    print("All tests executed")