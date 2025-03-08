# DistributedRobotic

DistributedRobotic is a simulated distributed system with controller and robots. It uses RPC for the communication with a controller and Message Oriented Middleware between robots.

## Features
- **Controller:**
    - Provides REST API with native sockets
    - Provides gRPC interface for communication with robots
    - Stores data and manages active robots
    - Connection checks for active robots
- **Robots:**
    - Uses gRPC to communicate with controller
    - Uses MQTT for communication between robots
    - Handles captain failure by automated election of new captain with bully algorithm
    - Multiple robots can be run
    - Automated connection with controller and MQTT broker after entering a robot name
- **Tests:**
    - Testing REST API endpoints and round trip time
    - Testing gRPC by communicating with controller and round trip time
    - Testing MQTT by running robots and starting captain election including a stress test
- **Others:**
    - Use Docker-Compose to run controller, robot, tests and MQTT broker in containers
    - Run Python scripts manually on your local system

## Installation & Execution
### 1. Containerized using Docker
#### Requirements
- Docker

#### Execution
```bash
  docker-compose build
  docker-compose up broker
  docker-compose up controller
  docker-compose up robot
  ```

### 2. On local system
#### Requirements
- Python 3.13
- Grpcio/Grpcio-tools 1.71.0rc2
- Paho-mqtt 2.1.0
- Eclipse mosquitto

#### Execution
```bash
  python ./src/controller/controller.py
  
  python ./src/robots/robot.py
  ```

## Runtime information
### REST API endpoints
| **Method** | **Endpoint**       | **Description**                    |
|------------|--------------------|------------------------------------|
| GET        | `/status`          | Get amount of active robots        |
| GET        | `/captain`         | Get the current captain            |
| GET        | `/health`          | Get the controller's health status |
| POST       | `/electCaptain`    | Start a new captain election       |

### Testing
This project includes both functional and non-functional tests:

1. **Functional test**: Validates the correct operation of the REST endpoints, gRPC methods and MQTT topics.
2. **Non-functional test**: Measures the round-trip time (RTT) of HTTP requests and gRPC method calls.

- Non-functional test results locally available in tests_grpc_rtt.txt and tests_http_rtt.txt

**(!) If testing without Docker HOST-variables in controller.py, robot.py, tests_http.py, tests_grpc.py and tests_mqtt.py need to be changed like described in the comments**

### Running tests
<u>Using Docker</u>
```bash
  docker-compose up tests
  ```
<u>Running locally</u>
```bash
  python ./tests/tests_http.py

  python ./tests/tests_grpc.py
  
  python ./tests/tests_mqtt.py
  ```

## Contributors
- **EricZones** - Developer

## Purpose
The project simulates remote communication between services with RPC and Message Oriented Middleware.
It was originally created for an evaluation at the university in 2025.