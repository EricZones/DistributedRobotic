from concurrent import futures
import time
import signal
import socket
import threading

import grpc
from proto import robot_service_pb2
from proto import robot_service_pb2_grpc

GRPC_PORT = 50051
HTTP_HOST = "0.0.0.0"  # local = localhost || docker = 0.0.0.0
HTTP_PORT = 8080

data = {"robots": [], "captain": None, "health": "OK"}
electionNeeded = False

class RobotServicer(robot_service_pb2_grpc.RobotServiceServicer):
    current_id = 0

    def GetRobots(self, request, context):
        if not data["robots"]:
            print("[gRPC] No robots available")
            return

        for robot in data["robots"]:
            yield robot_service_pb2.RobotData(
                id=robot["id"],
                name=robot["name"]
            )
            time.sleep(1)  # Simulated delay
        print(f"[gRPC] All {len(data["robots"])} robots transferred")

    def RegisterRobot(self, request, context):
        robot = {
            "id": self.current_id,
            "name": request.name
        }
        self.current_id += 1

        data["robots"].append(robot)
        print(f"[gRPC] Registered robot ({robot["id"]}, {robot["name"]})")
        return robot_service_pb2.RobotData(id=robot["id"], name=robot["name"])

    def UnregisterRobot(self, request, context):
        for robot in data["robots"]:
            if robot["id"] == request.id:
                data["robots"].remove(robot)
                print(f"[gRPC] Unregistered robot ({request.id})")

                if data["captain"] is not None and data["captain"]["id"] == request.id:
                    data["captain"] = None
                    print(f"[gRPC] Removed captain ({request.id})")

                return robot_service_pb2.Status(success=True)
        print(f"[gRPC] Robot {request.id} not found")
        return robot_service_pb2.Status(success=False)

    def CheckRobot(self, request, context):
        for robot in data["robots"]:
            if robot["id"] == request.id:
                print(f"[gRPC] Robot available ({request.id})")
                return robot_service_pb2.Status(success=True)
        print(f"[gRPC] Robot {request.id} not found")
        return robot_service_pb2.Status(success=False)

    def GetCaptain(self, request, context):
        if data["captain"] is None:
            print("[gRPC] No captain available")
            return robot_service_pb2.RobotData()
        else:
            print(f"[gRPC] Captain transferred ({data["captain"]["id"]})")
            return robot_service_pb2.RobotData(id=data["captain"]["id"], name=data["captain"]["name"])

    def HealthCheck(self, request, context):
        global electionNeeded
        for robot in data["robots"]:
            if robot["id"] == request.id:
                print(f"[gRPC] Robot {request.id} still connected")
                if electionNeeded:
                    electionNeeded = False
                    return robot_service_pb2.Commands(connected=True, elect=True)
                else:
                    return robot_service_pb2.Commands(connected=True, elect=False)
        print(f"[gRPC] Robot {request.id} not connected")
        return robot_service_pb2.Commands(connected=False, elect=False)

    def RegisterCaptain(self, request, context):
        captain = {
            "id": request.id,
            "name": request.name
        }
        data["captain"] = captain
        print(f"[gRPC] New captain elected ({request.id})")
        return robot_service_pb2.Status(success=True)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    robot_service_pb2_grpc.add_RobotServiceServicer_to_server(RobotServicer(), server)
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    server.start()
    print(f"[gRPC] Server running on port {GRPC_PORT}")

    shutdown_event.wait()
    print("[gRPC] Server stopping...")
    server.stop(0)
    # server.wait_for_termination()


def handle_http_request(request):
    try:
        lines = request.split("\r\n")
        method, path, _ = lines[0].split()
        if method == "GET":
            # Amount of active robots
            if path == "/status":
                return "HTTP/1.1 200 OK\r\n\r\n" + str(len(data["robots"]))
            # Current captain
            elif path == "/captain":
                return "HTTP/1.1 200 OK\r\n\r\n" + str(data["captain"])
            # Controller status
            elif path == "/health":
                return "HTTP/1.1 200 OK\r\n\r\n" + str(data["health"])
            else:
                return "HTTP/1.1 404 Not Found\r\n\r\nInvalid Endpoint"
        elif method == "POST":
            # Captain election
            if path == "/electCaptain":
                if not data["robots"]:
                    return "HTTP/1.1 400 Bad Request\r\n\r\nNo robot available"
                else:
                    global electionNeeded
                    electionNeeded = True
                    return "HTTP/1.1 200 OK\r\n\r\nNew captain election started"
            else:
                return "HTTP/1.1 404 Not Found\r\n\r\nInvalid Endpoint"
        else:
            return "HTTP/1.1 405 Method Not Allowed\r\n\r\nUnsupported Method"
    except Exception as e:
        return f"HTTP/1.1 500 Internal Server Error\r\n\r\nError: {e}"


def serve_http():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HTTP_HOST, HTTP_PORT))
        s.listen()
        s.settimeout(1)
        print(f"[HTTP] Server running on {HTTP_HOST}:{HTTP_PORT}")
        while not shutdown_event.is_set():
            try:
                conn, addr = s.accept()
                with conn:
                    print(f"[HTTP] Connected by {addr}")
                    request = conn.recv(1024).decode()
                    response = handle_http_request(request)
                    conn.sendall(response.encode())
            except socket.timeout:
                continue
        print("[HTTP] Server stopping...")


shutdown_event = threading.Event()

if __name__ == "__main__":
    def handle_termination(signum, frame):
        print("[Controller] All servers stopping...")
        shutdown_event.set()


    signal.signal(signal.SIGINT, handle_termination)
    signal.signal(signal.SIGTERM, handle_termination)

    grpc_thread = threading.Thread(target=serve, daemon=True)
    http_thread = threading.Thread(target=serve_http, daemon=True)
    grpc_thread.start()
    http_thread.start()

    while not shutdown_event.is_set():
        time.sleep(0.5)
    grpc_thread.join()
    http_thread.join()
    print("[Controller] All servers stopped")