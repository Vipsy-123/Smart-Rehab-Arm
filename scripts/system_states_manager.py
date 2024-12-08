# Importing all the required services
from planning_service import PlanningService
from flask import Flask, request, jsonify
from flask_cors import CORS
from redis_client import RedisClient
import json

app = Flask(__name__)
CORS(app, origins=["http://127.0.0.1:5500", "http://localhost:5500"])  # Enable CORS for frontend


class SystemStatesManager:
    def __init__(self):
        """
        Initialize all services required by the system.
        """
        print("Initializing System States Manager...")
        self.s_progress = 0.0
        self.s_no = [1, 2, 3, 4, 5]
        self.s_exercise = ['Elbow Rehabilitation', 'Wrist Rehabilitation']
        self.roll = 0.0
        self.pitch = 0.0
        self.emg = 0.0
        self.try_hard = ["Easy", "Medium", "Hard"]

        self.current_data = 0.0
        self.curr_s_no = 1  # Default to first session
        self.curr_s_exercise = 'Elbow Rehabilitation'  # Default to Elbow Rehab
        self.goal_data = 0.0

        # Dummy data for testing
        self.sensor_data = {
            'imu': {'roll': 0.0, 'pitch': 0.0, 'yaw': 0.0},
            'emg': {'analog': 0.0, 'try_hard': "Easy"},
            'progress': {'percentage': 100, 'target': 'Elbow Rehabilitation'},
            'session': {'number': 1, 'date': '2024-11-29', 'goal': 0, 'curr': 0}
        }

        self.redis_client = RedisClient()

    def progress_tracker(self):
        print("Progress Tracking")
        
        # Check if session number and exercise are set
        if self.curr_s_no is None or self.curr_s_exercise is None:
            print("Session number or exercise not set")
            return

        # Retrieve goals from Redis
        goals_raw = self.redis_client.redis.get("/redis/goals")
        
        try:
            # Parse goals from JSON
            goals = json.loads(goals_raw.decode('utf-8'))
            print(f"Retrieved goals: {goals}")

            # Construct goal key based on exercise and session number
            goal_key = f"{self.curr_s_exercise.lower().split()[0]}_{self.curr_s_no - 1}"
            
            # Get target reading for the current session
            target_data = goals.get(goal_key)
            
            if target_data is not None:
                # Set target reading in Redis
                self.redis_client.redis.set("/redis/target_reading", json.dumps({"target": target_data}))
                print(f"Set target reading for {goal_key}: {target_data}")

                # Retrieve sensor data from Redis
                imu_raw = self.redis_client.redis.get("/redis/imu")
                
                if imu_raw:
                    # Parse IMU data
                    imu_data = json.loads(imu_raw.decode('utf-8'))
                    
                    # Determine which reading to use based on exercise
                    if self.curr_s_exercise == "Wrist Rehabilitation":
                        reading = imu_data.get('roll', 0.0)
                    else:  # Elbow Rehabilitation
                        reading = imu_data.get('pitch', 0.0)
                    
                    # Set reading in Redis
                    self.redis_client.redis.set("/redis/reading", json.dumps({"reading": reading}))
                    print(f"Set reading: {reading}")
            else:
                print(f"No goal found for key: {goal_key}")
        
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"Error processing goals: {e}")

    # Add methods to set session number and exercise
    def set_session(self, s_no, s_exercise):
        """Set the current session number and exercise."""
        if s_no in self.s_no and s_exercise in self.s_exercise:
            self.curr_s_no = s_no
            self.curr_s_exercise = s_exercise
            print(f"Session set - Number: {s_no}, Exercise: {s_exercise}")
            return True
        else:
            print("Invalid session number or exercise")
            return False

    # Modify the routes to include setting session
    def session(self):
        data = request.json
        s_no = data.get('session_number')
        s_exercise = data.get('session_exercise')
        
        if s_no is not None and s_exercise is not None:
            success = self.set_session(s_no, s_exercise)
            if success:
                return jsonify({
                    "message": "Session set successfully", 
                    "session_number": s_no, 
                    "session_exercise": s_exercise
                }), 200
            else:
                return jsonify({"error": "Invalid session parameters"}), 400
        
        return jsonify({"error": "Missing session parameters"}), 400

    def calibrate(self):
        data = request.json
        calibrating = data.get('calibrating', False)
        print("Calibrating:", calibrating)
        return jsonify({"message": "Request received", "Calibrating status": calibrating}), 200

    # def session(self):
    #     data = request.json
    #     status = data.get('status', 0)
    #     print("Session status:", status)
    #     return jsonify({"message": "Request received", "Session status": status}), 200

    def get_data(self):
        self.progress_tracker()
        return jsonify(self.sensor_data)


# Initialize the SMS
sms = SystemStatesManager()

# Register routes with Flask
app.add_url_rule('/rehab/calibrate', 'calibrate', sms.calibrate, methods=['POST'])
app.add_url_rule('/rehab/session_status', 'session', sms.session, methods=['POST'])
app.add_url_rule('/rehab/get_data', 'get_data', sms.get_data, methods=['GET'])

if __name__ == "__main__":
    app.run(port=5000)
