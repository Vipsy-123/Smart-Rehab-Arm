import paho.mqtt.client as mqtt
import ssl
from redis_client import RedisClient
import json
import threading
import time


class CommsHandler:
    def __init__(self, broker, port, username=None, password=None):
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.client = mqtt.Client()
        self.received_messages = {}  # Store received messages for multiple topics

        self.client.tls_set(tls_version=ssl.PROTOCOL_TLSv1_2)

        # Assign callback methods
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_publish = self.on_publish

        # Set username and password if provided
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)

        self.redis_client = RedisClient()

        # Define handlers for specific topics
        self.topic_handlers = {
            "/rehab/imu": self.handle_imu_data,
            "/rehab/emg": self.handle_emg_data,

        }

    def connect(self):
        """Connect to the MQTT broker."""
        try:
            print(f"Connecting to MQTT Broker at {self.broker}:{self.port}...")
            self.client.connect(self.broker, self.port, keepalive=60)
        except Exception as e:
            print(f"Error connecting to broker: {e}")
            raise

    def on_connect(self, client, userdata, flags, rc):
        """Callback when the client connects to the broker."""
        if rc == 0:
            print("Connected to MQTT Broker successfully!")
        else:
            print(f"Failed to connect, return code {rc}")

    def subscribe(self, topics):
        """Subscribe to multiple topics."""
        try:
            if isinstance(topics, list):
                for topic in topics:
                    print(f"Subscribing to topic: {topic}")
                    self.client.subscribe(topic)
                    self.received_messages[topic] = []  # Initialize storage for topic messages
            else:
                print(f"Subscribing to single topic: {topics}")
                self.client.subscribe(topics)
                self.received_messages[topics] = []
        except Exception as e:
            print(f"Error subscribing to topic(s): {e}")

    def on_message(self, client, userdata, msg):
        """Callback when a message is received."""
        try:
            payload = msg.payload.decode()
            print(f"Received message on {msg.topic}: {payload}")
            if msg.topic in self.received_messages:
                self.received_messages[msg.topic].append(payload)

            # Call specific handler for the topic
            handler = self.topic_handlers.get(msg.topic)
            if handler:
                handler(payload)
            else:
                print(f"No handler defined for topic: {msg.topic}")
        except Exception as e:
            print(f"Error handling received message: {e}")

    def handle_imu_data(self, data):
        """Process IMU data and store it in Redis."""
        try:
            print(f"Handling IMU data: {data}")
            # Validate JSON before parsing
            try:
                parsed_data = json.loads(data)
            except json.JSONDecodeError as e:
                print(f"Invalid JSON format: {e}")
                # Optionally, you could try to correct the JSON or log the error
                return

            # Ensure the data has the expected structure
            if not isinstance(parsed_data, dict):
                print("IMU data is not a dictionary")
                return

            self.redis_client.redis.set("/redis/imu", json.dumps(parsed_data))
            print(f"Stored IMU data in Redis under key '/redis/imu'")
        except Exception as e:
            print(f"Error handling IMU data: {e}")

    def handle_emg_data(self, data):
        """Process EMG data and store it in Redis."""
        try:
            print(f"Handling EMG data: {data}")
            # Ensure data is parsed as JSON before storing
            parsed_data = json.loads(data)  # Convert string data to a Python dictionary
            self.redis_client.redis.set("/redis/emg", json.dumps(parsed_data))
            print(f"Stored EMG data in Redis under key '/redis/emg'")
        except Exception as e:
            print(f"Error handling EMG data: {e}")

    def publish(self, channel, key, value):
        """
        Publish a message to an MQTT channel and store it as a JSON key-value pair in Redis.
        """
        try:
            # Publish to MQTT
            self.client.publish(channel, json.dumps(value))
            print(f"Published to {channel}: {value}")

            # Store as JSON in Redis
            self.redis_client.redis.set(key, json.dumps(value))
            print(f"Stored key '{key}' with value: {value}")
        except Exception as e:
            print(f"Error publishing data: {e}")

    def fetch_and_publish_from_redis(self, redis_keys):
        """
        Fetch data from Redis keys and publish it to MQTT topics with the prefix '/rehab/'.
        """
        try:
            for redis_key in redis_keys:
                # Fetch raw JSON data from Redis
                data = self.redis_client.redis.get(redis_key)
                if data is not None:
                    # Decode and deserialize JSON data
                    data = json.loads(data.decode('utf-8'))
                    self.publish(channel=mqtt_topic, key=redis_key, value=data)
                    print(f"Fetched and deserialized data from Redis key '{redis_key}': {data}")
                    
                    # Construct MQTT topic
                    mqtt_topic = f"/rehab{redis_key.replace('/redis', '')}"
                    # Publish to MQTT topic
                    print(f"Published data from Redis key '{redis_key}' to MQTT topic '{mqtt_topic}'")
                else:
                    print(f"No data found for Redis key '{redis_key}'")
        except Exception as e:
            print(f"Error fetching or publishing data from Redis: {e}")

    def on_publish(self, client, userdata, mid):
        """Callback when a message is published."""
        print(f"Message published with mid: {mid}")


    def start_periodic_fetch_and_publish(self, redis_keys, interval=5):
        """
        Start a periodic task to fetch data from Redis and publish it to MQTT.
        """
        def periodic_task():
            while True:
                self.fetch_and_publish_from_redis(redis_keys)
                time.sleep(interval)

        # Run the periodic task in a separate thread
        thread = threading.Thread(target=periodic_task, daemon=True)
        thread.start()

    def start(self):
        """Start the MQTT client loop."""
        self.client.loop_start()

    def stop(self):
        """Stop the MQTT client loop."""
        self.client.loop_stop()
        self.client.disconnect()


# Example usage
if __name__ == "__main__":
    # Configure MQTT parameters
    BROKER = "b5cdaae2d7c94fa0a102a5133f99a1cd.s1.eu.hivemq.cloud"
    PORT = 8883
    USERNAME = "hivemq.webclient.1732348731048"
    PASSWORD = "9mt2.Qhw1bBTA;&LC,3x"

    # Topics to subscribe and publish
    SUB_TOPICS = ["/rehab/imu", "/rehab/emg"]
    REDIS_KEYS = ["/redis/calibrate", "/redis/timeout", "/redis/assist", "/redis/motor"]

    # Create an instance of the CommsHandler
    mqtt_client = CommsHandler(BROKER, PORT, USERNAME, PASSWORD)

    try:
        # Connect to the broker
        mqtt_client.connect()

        # Start the client loop
        mqtt_client.start()

        # Subscribe to the required topics
        mqtt_client.subscribe(SUB_TOPICS)

        # Start periodic fetch and publish from Redis
        mqtt_client.start_periodic_fetch_and_publish(redis_keys=REDIS_KEYS, interval=5)

        # Keep the script running to receive messages
        while True:
            pass  # Replace with specific logic if needed

    except KeyboardInterrupt:
        print("\nStopping MQTT Client...")
        mqtt_client.stop()
