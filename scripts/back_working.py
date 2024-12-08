from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from datetime import datetime
import paho.mqtt.client as mqtt
import ssl
import threading
import json
from redis_client import RedisClient  # Assuming Redis client is already defined

# Flask Application
app = Flask(__name__)
CORS(app, resources={r"/rehab/*": {"origins": ["http://127.0.0.1:5500", "http://localhost:5500"]}})

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Enhanced data structure
class RehabSession:
    def __init__(self):
        self.session_active = False
        self.session_number = 1  # Default to 1
        self.start_date = datetime.now().strftime("%m/%d/%Y")
        self.exercise_type = "Rehabilitation Exercise"
        self.imu_data = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        self.emg_data = {'analog': 0.0}
        self.progress = {
            'percentage': 50,  # Default to 45% to match frontend
            'target': "Rehabilitation Exercise"
        }
        self.status = 0
        self.assist = 0
        self.timeout = 0
        self.goals = [-25,-50,-75,-90, -120]

# Global session instance
current_session = RehabSession()

@app.route('/rehab/session_status', methods=['POST'])
def manage_session():
    data = request.json
    status = data.get('status', 0)
    
    if status == 1:  # Start session
        current_session.session_active = True
        current_session.session_number += 1
        current_session.start_date = datetime.now().strftime("%m/%d/%Y")
        current_session.progress['percentage'] = 0
        current_session.status = 1
        logger.info(f"Session started: Session {current_session.session_number}")
        return jsonify({
            "message": "Session started successfully", 
            "session": {
                "number": current_session.session_number,
                "date": current_session.start_date
            }
        }), 200
        current_session.run_fuzzy_logic()
    
    elif status == 0:  # Stop session
        if current_session.session_active:
            current_session.status = 0
            current_session.session_active = False
            logger.info(f"Session stopped: Session {current_session.session_number}")
            return jsonify({"message": "Session stopped successfully"}), 200
        else:
            return jsonify({"message": "No active session to stop"}), 400

@app.route('/rehab/update_sensor_data', methods=['POST'])
def update_sensor_data():
    data = request.json
    
    # Update IMU data
    if 'imu' in data:
        current_session.imu_data['x'] = data['imu'].get('x', current_session.imu_data['x'])
        current_session.imu_data['y'] = data['imu'].get('y', current_session.imu_data['y'])
        current_session.imu_data['z'] = data['imu'].get('z', current_session.imu_data['z'])
    
    # Update EMG data
    if 'emg' in data:
        current_session.emg_data['analog'] = data['emg'].get('analog', current_session.emg_data['analog'])
    
    # Update progress
    if 'progress' in data:
        current_session.progress['percentage'] = data['progress'].get('percentage', current_session.progress['percentage'])
    
    return jsonify({"message": "Sensor data updated and published successfully"}), 200


@app.route('/rehab/calibrate', methods=['POST'])
def calibrate():
    # Reset sensor data to initial state
    current_session.imu_data = {'x': 0.0, 'y': 0.0, 'z': 0.0}
    current_session.emg_data = {'analog': 0.0}
    current_session.status = 2
    logger.info("Calibration performed")
    return jsonify({
        "message": "Calibration successful",
        "calibration_status": True
    }), 200

@app.route('/rehab/get_data', methods=['GET'])
def get_data():

        # Publish to MQTT topics
    try:
        mqtt_client.client.publish("/rehab/assist", json.dumps({"assist": True}))
        mqtt_client.client.publish("/rehab/status", json.dumps({"status": 1}))
        mqtt_client.client.publish("/rehab/timeout", json.dumps({"timeout": 30}))

        logger.info("Published data to MQTT topics")
    except Exception as e:
        logger.error(f"Failed to publish to MQTT: {e}")
        return jsonify({"message": "Sensor data updated, but MQTT publish failed"}), 500
        
    return jsonify({
        "imu": current_session.imu_data,
        "emg": current_session.emg_data,
        "progress": current_session.progress,
        "session": {
            "number": current_session.session_number,
            "date": current_session.start_date
        }
    }), 200

# MQTT Client
class CommsHandler:
    def __init__(self, broker, port, username=None, password=None):
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.client = mqtt.Client()
        self.redis_client = RedisClient()

        self.client.tls_set(tls_version=ssl.PROTOCOL_TLSv1_2)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)

    def connect(self):
        self.client.connect(self.broker, self.port, keepalive=60)

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker successfully!")
            self.client.subscribe([("/rehab/imu", 0), ("/rehab/emg", 0)])
        else:
            print(f"Failed to connect, return code {rc}")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            print(f"Received payload on topic {msg.topic}: {payload}")

            if msg.topic == "/rehab/imu":
                # Extract specific IMU data fields
                imu_x = payload.get("x", current_session.imu_data["x"])
                imu_y = payload.get("y", current_session.imu_data["y"])
                imu_z = payload.get("z", current_session.imu_data["z"])
                # Update current_session's IMU data
                current_session.imu_data = {"x": imu_x, "y": imu_y, "z": imu_z}
                print(f"Updated IMU data: {current_session.imu_data}")

            elif msg.topic == "/rehab/emg":
                # Extract specific EMG data fields
                emg_analog = payload.get("analog", current_session.emg_data["analog"])
                # Update current_session's EMG data
                current_session.emg_data = {"analog": emg_analog}
                print(f"Updated EMG data: {current_session.emg_data}")

            else:
                print(f"Unhandled topic: {msg.topic}")

        except json.JSONDecodeError:
            print(f"Invalid JSON payload on topic {msg.topic}: {msg.payload.decode()}")
        except Exception as e:
            print(f"Error processing message on topic {msg.topic}: {e}")


    def start(self):
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()

# Running Flask and MQTT
if __name__ == '__main__':
    mqtt_client = CommsHandler(
        broker="b5cdaae2d7c94fa0a102a5133f99a1cd.s1.eu.hivemq.cloud",
        port=8883,
        username="hivemq.webclient.1732348731048",
        password="9mt2.Qhw1bBTA;&LC,3x"
    )

    mqtt_client.connect()
    threading.Thread(target=mqtt_client.start).start()

    app.run(port=5000, debug=True)
