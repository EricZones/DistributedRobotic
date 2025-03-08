import signal
import time
import threading
import paho.mqtt.client as mqtt

import grpc
from proto import robot_service_pb2
from proto import robot_service_pb2_grpc

# Configuration
GRPC_HOST = "controller"  # local = localhost || docker = controller
GRPC_PORT = 50051
MQTT_HOST = "broker"  # local = localhost || docker = broker
MQTT_PORT = 1883

# MQTT topics
TOPIC_ELECTION_START = "robots/election/start"
TOPIC_ELECTION_CANDIDATE = "robots/election/candidate"
TOPIC_ELECTION_RESULT = "robots/election/result"
TOPIC_STATUS = "robots/status"

# Robot data
id = -1
name = "default"
captain = False
stub = None  # gRPC
client = None  # MQTT

# MQTT clients
HEARTBEAT_INTERVAL = 2
HEARTBEAT_TIMEOUT = 10
election_candidates = []
recent_heartbeat = None  # time.time() if election at start


## gRPC methods ##

def register():
    global id, name, captain, stub
    response = stub.RegisterRobot(robot_service_pb2.RobotInfo(name=name))
    id = response.id
    captain = False
    print(f"[gRPC] {name} with ID={id} and Captain={captain} connected")


def unregister():
    global id, name, stub
    response = stub.UnregisterRobot(robot_service_pb2.RobotData(id=id, name=name))
    if (response.success == True):
        print("[gRPC] Robot disconnected")
    else:
        print("[gRPC] Robot could not disconnect")


def checkHealth():
    global id, name, stub
    response = stub.HealthCheck(robot_service_pb2.RobotData(id=id, name=name))
    if response.connected:
        print("[gRPC] Robot is connected")
        if response.elect:
            startElection()
    else:
        print("[gRPC] Robot is disconnected")


def registerCaptain():
    global id, name, stub
    response = stub.RegisterCaptain(robot_service_pb2.RobotData(id=id, name=name))
    if response.success:
        print("[gRPC] Robot registered as captain")
    else:
        print("[gRPC] Captain registration failed")


## MQTT methods ##

def on_connect(client, userdata, flags, reason_code, properties):
    print(f"[MQTT] Robot connected: {reason_code}")
    client.subscribe([(TOPIC_ELECTION_START, 0), (TOPIC_ELECTION_CANDIDATE, 0),
                      (TOPIC_ELECTION_RESULT, 0), (TOPIC_STATUS, 0)])


def on_message(client, userdata, msg):
    global id, captain, election_candidates
    topic = msg.topic
    payload = msg.payload.decode()

    print(f"[MQTT] Message received for {topic}: {payload}")

    if topic == TOPIC_STATUS:
        global recent_heartbeat
        recent_heartbeat = time.time()
    elif topic == TOPIC_ELECTION_START:
        threading.Thread(target=electCaptain, daemon=True).start()
    elif topic == TOPIC_ELECTION_CANDIDATE:
        if not id == int(payload):
            print(f"[MQTT] Robot ({payload}) candidates as captain")
        election_candidates.append(int(payload))
    elif topic == TOPIC_ELECTION_RESULT:
        if int(payload) == id:
            captain = True
            print("[MQTT] Robot elected as captain")
            registerCaptain()
        else:
            captain = False
            print(f"[MQTT] New captain is ({payload})")


def electCaptain():
    global client, id, election_candidates, recent_heartbeat
    print("[MQTT] New captain election started")
    recent_heartbeat = time.time()
    election_candidates = []
    print(f"[MQTT] Candidating for captain election ({id})")
    client.publish(TOPIC_ELECTION_CANDIDATE, id)

    time.sleep(3)  # Waiting for other candidates

    if id == max(election_candidates):
        print(f"[MQTT] Publishing myself as captain ({id})")
        client.publish(TOPIC_ELECTION_RESULT, id)
    else:
        print("[MQTT] Rejecting candidation...")


def startElection():
    global client, id, recent_heartbeat
    print("[MQTT] Starting new captain election...")
    recent_heartbeat = time.time()
    client.publish(TOPIC_ELECTION_START, id)


def heartbeat():
    global client, id
    client.publish(TOPIC_STATUS, id)


def checkHeartbeat():
    global recent_heartbeat
    if recent_heartbeat is not None and time.time() - recent_heartbeat > HEARTBEAT_TIMEOUT:
        print("[MQTT] Missing heartbeat from captain")
        startElection()


## Thread methods ##

def run_grpc():
    global stub
    with grpc.insecure_channel(f"{GRPC_HOST}:{GRPC_PORT}") as channel:
        stub = robot_service_pb2_grpc.RobotServiceStub(channel)
        print("[Robot] Started gRPC client")
        register()

        while not shutdown_event.is_set():
            checkHealth()
            time.sleep(10)
        print("[Robot] gRPC client stopping...")
        unregister()
        channel.close()


def run_mqtt():
    global id, client, captain
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT, 60)

    client.loop_start()
    while not shutdown_event.is_set():
        if captain:
            heartbeat()
        else:
            checkHeartbeat()
        time.sleep(HEARTBEAT_INTERVAL)
    print("[Robot] MQTT client stopping...")
    client.loop_stop()
    client.disconnect()


shutdown_event = threading.Event()

if __name__ == "__main__":
    def handle_termination(signum, frame):
        print("[Robot] All processes stopping...")
        shutdown_event.set()


    signal.signal(signal.SIGINT, handle_termination)
    signal.signal(signal.SIGTERM, handle_termination)

    print("[Robot] New client launched")
    name = input("[Robot] Enter a name... ")

    grpc_thread = threading.Thread(target=run_grpc, daemon=True)
    mqtt_thread = threading.Thread(target=run_mqtt, daemon=True)

    grpc_thread.start()
    mqtt_thread.start()

    while not shutdown_event.is_set():
        time.sleep(0.5)
    grpc_thread.join()
    mqtt_thread.join()
    print("[Robot] All processes stopped")