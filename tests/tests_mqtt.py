import time
import sys
import threading
import paho.mqtt.client as mqtt

# Configuration
MQTT_HOST = "broker" # local = localhost || docker = broker
MQTT_PORT = 1883

# MQTT topics
TOPIC_ELECTION_START = "robots/election/start"
TOPIC_ELECTION_CANDIDATE = "robots/election/candidate"
TOPIC_ELECTION_RESULT = "robots/election/result"
TOPIC_STATUS = "robots/status"

# MQTT clients
NUM_ROBOTS = 5  # testing robot amount
HEARTBEAT_TIMEOUT = 10
HEARTBEAT_INTERVAL = 2
MQTT_MESSAGE_COUNT = 20  # stresstest

class Robot:
    def __init__(self, id):
        self.id = id
        self.captain = False
        self.election_candidates = []
        self.recent_heartbeat = None
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_message = self.on_message
        self.client.connect(MQTT_HOST, MQTT_PORT, 60)
        self.client.subscribe([(TOPIC_ELECTION_START, 0), (TOPIC_ELECTION_CANDIDATE, 0), (TOPIC_ELECTION_RESULT, 0), (TOPIC_STATUS, 0)])
        self.client.loop_start()
        
    def run(self):
        while True:
            if self.captain:
                self.heartbeat()
            else:
                self.checkHeartbeat()
            time.sleep(HEARTBEAT_INTERVAL)

    def startElection(self):
        print("[MQTT] Starting new captain election...")
        self.recent_heartbeat = time.time()
        self.client.publish(TOPIC_ELECTION_START, self.id)
    
    def electCaptain(self):
        print("[MQTT] New captain election started")
        self.recent_heartbeat = time.time()
        self.election_candidates = []
        print(f"[MQTT] Candidating for captain election ({self.id})")
        self.client.publish(TOPIC_ELECTION_CANDIDATE, self.id)
    
        time.sleep(3) # Waiting for other candidates
    
        if self.id == max(self.election_candidates):
            print(f"[MQTT] Publishing myself as captain ({self.id})")
            self.client.publish(TOPIC_ELECTION_RESULT, self.id)
        else:
            print("[MQTT] Rejecting candidation...")
    
    def heartbeat(self):
        self.client.publish(TOPIC_STATUS, self.id)
    
    def checkHeartbeat(self):
        if self.recent_heartbeat is not None and time.time() - self.recent_heartbeat > HEARTBEAT_TIMEOUT:
            print("[MQTT] Missing heartbeat from captain")
            self.startElection()

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()

        print(f"[MQTT] Message received for {topic}: {payload}")

        if topic == TOPIC_STATUS:
            self.recent_heartbeat = time.time()
        elif topic == TOPIC_ELECTION_START:
            threading.Thread(target = self.electCaptain, daemon = True).start()
        elif topic == TOPIC_ELECTION_CANDIDATE:
            if not self.id == int(payload):
                print(f"[MQTT] Robot ({payload}) candidates as captain")
            self.election_candidates.append(int(payload))
        elif topic == TOPIC_ELECTION_RESULT:
            if int(payload) == self.id:
                self.captain = True
                print("[MQTT] Robot elected as captain")
            else:
                self.captain = False
                print(f"[MQTT] New captain is ({payload})")


def stress_test(): # High amount of messages
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    print(f"[Stress Test] Sending {MQTT_MESSAGE_COUNT} messages...")
    for _ in range(MQTT_MESSAGE_COUNT):
        client.publish(TOPIC_STATUS, "test")
    print("[Stress Test] Messages sent")

if __name__ == "__main__":
    robots = [Robot(i) for i in range(NUM_ROBOTS)]
    for robot in robots:
        threading.Thread(target=robot.run).start()
        
    print("\n=== Leader election test ===")
    time.sleep(1)
    robots[0].client.publish(TOPIC_ELECTION_START, robots[0].id)

    print("\n=== High message amount test ===")
    stress_test()
    sys.exit()
