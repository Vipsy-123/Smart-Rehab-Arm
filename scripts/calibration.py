import json
from redis_client import RedisClient


class CalibrationService:
    def __init__(self):
        self.redis_client = RedisClient()
        self.base_values = {
            'imu': None,
            'emg': None
        }
        self.calibration_topic = "rehab/calibration"

    def calibrate_imu_data(self, imu_data):
        """Calibrate the IMU data (e.g., filtering, averaging)."""
        # Here, you can add your calibration logic (e.g., filter noise, adjust for offsets).
        calibrated_imu = imu_data  # Placeholder for calibration logic
        self.base_values['imu'] = calibrated_imu
        self.store_and_publish('imu', calibrated_imu)

    def calibrate_emg_data(self, emg_data):
        """Calibrate the EMG data (e.g., normalization, baseline adjustment)."""
        # Add your EMG calibration logic (e.g., noise reduction, baseline correction).
        calibrated_emg = emg_data  # Placeholder for calibration logic
        self.base_values['emg'] = calibrated_emg
        self.store_and_publish('emg', calibrated_emg)

    def store_and_publish(self, data_type, data):
        """Store the data in Redis and publish it to a topic."""
        key = f"base:{data_type}_value"
        # Store the data in Redis
        self.redis_client.redis.set(key, json.dumps(data))
        print(f"Stored {data_type} calibration data in Redis with key {key}")
        
        # Publish the calibrated value to Redis channel
        self.redis_client.publish(self.calibration_topic, json.dumps({
            'type': data_type,
            'value': data
        }))
        print(f"Published {data_type} calibration data to {self.calibration_topic}")

    def get_calibration_values(self):
        """Retrieve the stored base calibration values."""
        return self.base_values


# Example usage:
if __name__ == "__main__":
    calibration_service = CalibrationService()

    # Example IMU and EMG data (replace with actual sensor data)
    imu_data = {'x': 0.5, 'y': 0.2, 'z': -0.3}
    emg_data = {'muscle_1': 250, 'muscle_2': 300, 'muscle_3': 150}

    # Calibrate data
    calibration_service.calibrate_imu_data(imu_data)
    calibration_service.calibrate_emg_data(emg_data)

    # Retrieve calibration values
    base_values = calibration_service.get_calibration_values()
    print("Base Calibration Values:", base_values)
