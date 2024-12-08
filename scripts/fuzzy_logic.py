import numpy as np
import skfuzzy as fuzz
from skfuzzy.control import Antecedent, Consequent, Rule, ControlSystem, ControlSystemSimulation
import redis
import time
import ast

class AssistanceService:
    def __init__(self, redis_host='localhost', redis_port=6379):
        # Connect to Redis
        self.redis_client = redis.StrictRedis(host=redis_host, port=redis_port, db=0)

        # Define Fuzzy variables
        self.define_fuzzy_logic()

    def define_fuzzy_logic(self):
        # Define input variables
        self.emg_signal = Antecedent(np.arange(0, 101, 1), 'emg_signal')  # EMG: 0 to 100% normalized amplitude
        self.current_reading = Antecedent(np.arange(0, 151, 1), 'current_reading')  # Current sensor reading (0 to 150)
        self.goal_difference = Antecedent(np.arange(-100, 101, 1), 'goal_difference')  # Difference between goal and reading

        # Define output variables
        self.assist_decision = Consequent(np.arange(0, 101, 1), 'assist_decision')  # Decision to assist (0: No, 100: Yes)
        self.timeout_duration = Consequent(np.arange(0, 31, 1), 'timeout_duration')  # Timeout in seconds (0 to 30)

        # Membership functions for EMG signal
        self.emg_signal['low'] = fuzz.trapmf(self.emg_signal.universe, [0, 0, 20, 40])
        self.emg_signal['moderate'] = fuzz.trimf(self.emg_signal.universe, [20, 50, 80])
        self.emg_signal['high'] = fuzz.trapmf(self.emg_signal.universe, [60, 80, 100, 100])

        # Membership functions for current reading and goal difference
        self.current_reading['small'] = fuzz.trapmf(self.current_reading.universe, [0, 0, 30, 50])
        self.current_reading['moderate'] = fuzz.trimf(self.current_reading.universe, [30, 75, 120])
        self.current_reading['large'] = fuzz.trapmf(self.current_reading.universe, [100, 120, 150, 150])

        self.goal_difference['near'] = fuzz.trapmf(self.goal_difference.universe, [-10, 0, 0, 10])
        self.goal_difference['below_goal'] = fuzz.trapmf(self.goal_difference.universe, [-100, -100, -30, -10])
        self.goal_difference['above_goal'] = fuzz.trapmf(self.goal_difference.universe, [10, 30, 100, 100])

        # Membership functions for assist decision
        self.assist_decision['no'] = fuzz.trimf(self.assist_decision.universe, [0, 0, 50])
        self.assist_decision['maybe'] = fuzz.trimf(self.assist_decision.universe, [25, 50, 75])
        self.assist_decision['yes'] = fuzz.trimf(self.assist_decision.universe, [50, 100, 100])

        # Membership functions for timeout duration
        self.timeout_duration['short'] = fuzz.trapmf(self.timeout_duration.universe, [0, 0, 5, 10])
        self.timeout_duration['medium'] = fuzz.trimf(self.timeout_duration.universe, [5, 15, 25])
        self.timeout_duration['long'] = fuzz.trapmf(self.timeout_duration.universe, [20, 25, 30, 30])

        # Define fuzzy rules
        self.define_rules()

    def define_rules(self):
        # Assistance rules
        rule1 = Rule(self.emg_signal['low'] & self.goal_difference['below_goal'], 
                     (self.assist_decision['yes'], self.timeout_duration['short']))
        rule2 = Rule(self.emg_signal['moderate'] & self.goal_difference['near'], 
                     (self.assist_decision['maybe'], self.timeout_duration['medium']))
        rule3 = Rule(self.emg_signal['high'] & self.goal_difference['above_goal'], 
                     (self.assist_decision['no'], self.timeout_duration['long']))
        rule4 = Rule(self.current_reading['small'] & self.emg_signal['low'], 
                     (self.assist_decision['yes'], self.timeout_duration['short']))
        rule5 = Rule(self.current_reading['moderate'] & self.goal_difference['near'], 
                     (self.assist_decision['maybe'], self.timeout_duration['medium']))
        rule6 = Rule(self.current_reading['large'] & self.goal_difference['above_goal'], 
                     (self.assist_decision['no'], self.timeout_duration['long']))

        # Create a control system
        self.assist_control = ControlSystem([rule1, rule2, rule3, rule4, rule5, rule6])
        self.assist_simulation = ControlSystemSimulation(self.assist_control)

    def safe_eval(self, data):
        try:
            return ast.literal_eval(data)  # Safely evaluate the string as a dictionary
        except (ValueError, SyntaxError):
            print(f"Failed to parse data: {data}")
            return {}

    def run(self):
        while True:
            try:
                # Fetch and process goals
                goals_raw = self.redis_client.get('/redis/goals')
                goals = self.safe_eval(goals_raw.decode()) if goals_raw else {}
                target = float(goals.get("target", 0))

                # Fetch and process EMG data
                emg_raw = self.redis_client.get('/redis/emg')
                emg_data = self.safe_eval(emg_raw.decode()) if emg_raw else {}
                emg = float(emg_data.get('data', 0))

                # Fetch and process IMU data
                imu_raw = self.redis_client.get('/redis/imu')
                imu_data = self.safe_eval(imu_raw.decode()) if imu_raw else {}
                rpy = imu_data.get('rpy', [0, 0, 0])

                # Fetch and process current reading
                reading_raw = self.redis_client.get('/redis/reading')
                reading = float(reading_raw.decode()) if reading_raw else 0

                # Calculate goal difference
                goal_diff = reading - target

                # Set inputs to fuzzy logic system
                self.assist_simulation.input['emg_signal'] = emg
                self.assist_simulation.input['current_reading'] = reading
                self.assist_simulation.input['goal_difference'] = goal_diff

                # Compute the fuzzy output
                self.assist_simulation.compute()

                assist_decision = self.assist_simulation.output['assist_decision']
                timeout_duration = self.assist_simulation.output['timeout_duration']

                print(f"Assist Decision: {assist_decision:.2f}, Timeout: {timeout_duration:.2f}s")
            except Exception as e:
                print(f"Error occurred: {e}")
            time.sleep(1)

# Run the service
assistance_service = AssistanceService()
assistance_service.run()
