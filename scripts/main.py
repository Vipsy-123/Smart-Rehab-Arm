import numpy as np
import skfuzzy as fuzz
from skfuzzy.control import Antecedent, Consequent, Rule, ControlSystem, ControlSystemSimulation
import redis
import time
import threading
from skfuzzy import control as ctrl
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from datetime import datetime
import paho.mqtt.client as mqtt
import ssl
import json
from redis_client import RedisClient  # Assuming Redis client is already defined

# Flask Application
app = Flask(__name__)
CORS(app, resources={r"/rehab/*": {"origins": ["http://127.0.0.1:5500", "http://localhost:5500"]}})

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AssistanceService:
    def __init__(self, session, redis_host='localhost', redis_port=6379):
        self.session = session
        self.redis_client = redis.StrictRedis(host=redis_host, port=redis_port, db=0)
        self.define_fuzzy_logic()
        self._stop_fuzzy_logic = threading.Event()

    def define_fuzzy_logic(self):
        # Input variables
        self.goal_difference = ctrl.Antecedent(universe=np.arange(0, 121, 1), label="goal_difference")
        self.emg_signal = ctrl.Antecedent(universe=np.arange(0, 4096, 1), label="emg_signal")

        # Output variable
        self.assist_decision = ctrl.Consequent(universe=np.arange(0, 101, 1), label="assist_decision")
        self.timeout_duration = ctrl.Consequent(universe=np.arange(0, 31, 1), label="timeout_duration")

        # Membership functions 
        self.goal_difference['low_diff'] = fuzz.trimf(self.goal_difference.universe, [0, 0, 20])
        self.goal_difference['medium_diff'] = fuzz.trimf(self.goal_difference.universe, [20, 35, 50])
        self.goal_difference['large_diff'] = fuzz.trimf(self.goal_difference.universe, [50, 85, 120])

        self.emg_signal['low'] = fuzz.trapmf(self.emg_signal.universe, [0, 0, 400, 600])
        self.emg_signal['medium'] = fuzz.trapmf(self.emg_signal.universe, [500, 700, 800, 1000])
        self.emg_signal['high'] = fuzz.trapmf(self.emg_signal.universe, [900, 1100, 1500, 1500])

        self.assist_decision['no'] = fuzz.trimf(self.assist_decision.universe, [0, 0, 50])
        self.assist_decision['maybe'] = fuzz.trimf(self.assist_decision.universe, [25, 50, 75])
        self.assist_decision['yes'] = fuzz.trimf(self.assist_decision.universe, [50, 100, 100])

        self.timeout_duration['short'] = fuzz.trimf(self.timeout_duration.universe, [0, 0, 5])
        self.timeout_duration['medium'] = fuzz.trimf(self.timeout_duration.universe, [5, 10, 15])
        self.timeout_duration['long'] = fuzz.trimf(self.timeout_duration.universe, [15, 22.5, 30])

        self.define_rules()

    def define_rules(self):
        # Rules
        # Low difference rules
        rule1 = ctrl.Rule(self.goal_difference['low_diff'] & self.emg_signal['low'], self.assist_decision['no'])
        rule2 = ctrl.Rule(self.goal_difference['low_diff'] & self.emg_signal['medium'], self.assist_decision['maybe'])
        rule3 = ctrl.Rule(self.goal_difference['low_diff'] & self.emg_signal['high'], self.assist_decision['yes'])

        # Medium difference rules
        rule4 = ctrl.Rule(self.goal_difference['medium_diff'] & self.emg_signal['low'], self.assist_decision['no'])
        rule5 = ctrl.Rule(self.goal_difference['medium_diff'] & self.emg_signal['medium'], self.assist_decision['maybe'])
        rule6 = ctrl.Rule(self.goal_difference['medium_diff'] & self.emg_signal['high'], self.assist_decision['yes'])

        # Large difference rules
        rule7 = ctrl.Rule(self.goal_difference['large_diff'] & self.emg_signal['low'], self.assist_decision['no'])
        rule8 = ctrl.Rule(self.goal_difference['large_diff'] & self.emg_signal['medium'], self.assist_decision['maybe'])
        rule9 = ctrl.Rule(self.goal_difference['large_diff'] & self.emg_signal['high'], self.assist_decision['yes'])


        # Control system
        assist_control = ctrl.ControlSystem([rule1, rule2, rule3, rule4 , rule5 , rule6, rule7, rule8, rule9])
        self.assist_decision_sim = ctrl.ControlSystemSimulation(assist_control)

        # timeout_control = ctrl.ControlSystem([rule4, rule5, rule6])
        # self.timeout_sim = ctrl.ControlSystemSimulation(timeout_control)

    def run_fuzzy_logic(self):
        while current_session.session_active:
            try:
                target = current_session.goals[current_session.session_number - 1]
                imu_reading = current_session.imu_data['x']
                emg = current_session.emg_data['analog']

                goal_diff = imu_reading - target

                # Set inputs for assist decision simulation
                self.assist_decision_sim.input['emg_signal'] = emg  # Ensure it's in the correct range
                self.assist_decision_sim.input['goal_difference'] = goal_diff

                # Compute assist decision
                self.assist_decision_sim.compute()
                assist_decision = self.assist_decision_sim.output

                # Set inputs for timeout duration simulation
                # self.timeout_sim.input['goal_difference'] = goal_diff

                # Compute timeout duration
                # self.timeout_sim.compute()
                # timeout_duration = self.timeout_sim.output['timeout_duration']

                # Update current session data
                current_session.assist = assist_decision
                # current_session.timeout = timeout_duration
                # print(assist_decision)
                print(f"Assist Decision: {assist_decision}")
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"Error in fuzzy logic processing: {e}")
                break

        logger.info("Fuzzy logic processing stopped")


    def stop_fuzzy_logic(self):
        self._stop_fuzzy_logic.set()


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
            'percentage': 0,  # Start at 0%
            'target': "Rehabilitation Exercise"
        }
        self.status = 0
        self.assist = 0
        self.timeout = 0
        self.goals = [25, 50, 75, 90, 120]
        
        # Create AssistanceService instance
        self.assistance_service = AssistanceService(self)
        self._fuzzy_thread = None

# Global session instance
current_session = RehabSession()

@app.route('/rehab/session_status', methods=['POST'])
def manage_session():
    data = request.json
    status = data.get('status', 0)
    
    if status == 1:  # Start session
        # Reset session parameters
        current_session.session_active = True
       
        current_session.start_date = datetime.now().strftime("%m/%d/%Y")
        current_session.progress['percentage'] = 0
        current_session.status = 1
        
        # Reset stop event for fuzzy logic
        current_session.assistance_service._stop_fuzzy_logic.clear()
        
        # Start fuzzy logic processing in a separate thread
        current_session._fuzzy_thread = threading.Thread(
            target=current_session.assistance_service.run_fuzzy_logic
        )
        current_session._fuzzy_thread.start()
        
        logger.info(f"Session started: Session {current_session.session_number}")
        return jsonify({
            "message": "Session started successfully", 
            "session": {
                "number": current_session.session_number,
                "date": current_session.start_date
            }
        }), 200
    
    elif status == 0:  # Stop session
        if current_session.session_active:
            # Stop fuzzy logic processing
            current_session.assistance_service.stop_fuzzy_logic()
            
            # Reset session parameters
            current_session.session_active = False
            current_session.status = 0
            current_session.progress['percentage'] = 0
            
            logger.info(f"Session stopped: Session {current_session.session_number}")
            return jsonify({"message": "Session stopped successfully"}), 200
        else:
            return jsonify({"message": "No active session to stop"}), 400


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

@app.route('/rehab/change_session', methods=['POST'])
def change_session():
    try:
        # Parse JSON payload
        data = request.json
        print("Payload Received:", data)

        if not data:
            return jsonify({"error": "Invalid JSON payload"}), 400
        
        # Retrieve the new session number from the request
        new_session = data.get('new_session')
        print("New Session:", new_session)

        # Validate and update the session number
        if new_session is None:
            return jsonify({"error": "Session number must be an integer"}), 400

        current_session.session_number = int(new_session)

        # Respond with success
        return jsonify({
            "message": "Session updated successfully",
            "current_session": current_session.session_number
        }), 200

    except Exception as e:
        import traceback
        print("Exception occurred:", traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/rehab/get_data', methods=['GET'])
def get_data():

        # Publish to MQTT topics
    try:
        mqtt_client.client.publish("/rehab/assist", json.dumps({"assist": current_session.assist}))
        mqtt_client.client.publish("/rehab/status", json.dumps({"status": current_session.status}))
        mqtt_client.client.publish("/rehab/timeout", json.dumps({"timeout": current_session.timeout}))

        logger.info("Published data to MQTT topics")

        target = current_session.goals[current_session.session_number - 1]
        current = current_session.imu_data['x']
        current_session.progress['percentage'] = f"{(current / target) * 100:.2f}"

        print(f" Progress is {current_session.progress['percentage']} for session {current_session.session_number}")

        if current_session.progress['percentage'] == 100.0 : 
            print("Session Completed")
            current_session.session_active = False
            current_session.status = 0
    except Exception as e:
        logger.error(f"Failed to publish to MQTT: {e}")
        return jsonify({"message": "Sensor data updated, but MQTT publish failed"}), 500
        
    return jsonify({
        "imu": current_session.imu_data,
        "emg": current_session.emg_data,
        "progress": current_session.progress,
        "session": {
            "number": current_session.session_number,
            "date": current_session.start_date,
            "active_status": current_session.session_active
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
                print("here")
                # Extract specific IMU data fields
                imu_x = payload.get("x", current_session.imu_data["x"])
                imu_y = payload.get("y", current_session.imu_data["y"])
                imu_z = payload.get("z", current_session.imu_data["z"])
                print(imu_x)
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



# {"x" : 25 , "y": 20 , "z":3}