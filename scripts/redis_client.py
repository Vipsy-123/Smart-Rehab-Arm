import subprocess
import redis
import time
import os
import threading
import shutil

class RedisClient:
    def __init__(self, host='127.0.0.1', port=6379, db=0):
        self.host = host
        self.port = port
        self.db = db
        
        # Ensure Redis server is running
        self.ensure_redis_running()

        # Connect to Redis
        self.redis = redis.Redis(host=self.host, port=self.port, db=self.db)
        self.pubsub = self.redis.pubsub()

    def ensure_redis_running(self):
        """Start Redis server if it is not running."""
        if not self.is_redis_running():
            print("Redis server is not running. Starting Redis server...")
            self.start_redis_server()

        # Wait for Redis to be ready (can take a few seconds)
        time.sleep(2)

    def is_redis_running(self):
        """Check if Redis server is already running on the specified port."""
        try:
            # Try to connect to Redis to check if it's running
            r = redis.Redis(host=self.host, port=self.port)
            r.ping()
            return True
        except redis.ConnectionError:
            return False

    def start_redis_server(self):
        """Start the Redis server using subprocess."""
        redis_server_path = shutil.which("redis-server")
        if not redis_server_path:
            raise FileNotFoundError("Redis server executable not found. Ensure Redis is installed.")
        else:
            print(f"Redis server found at: {redis_server_path}")

        if not os.path.isfile(redis_server_path):
            print(f"Redis server executable not found at {redis_server_path}. Please install Redis.")
            return

        # Start the Redis server as a subprocess
        subprocess.Popen([redis_server_path])

    def publish(self, channel, message):
        """Publish a message to a Redis channel."""
        self.redis.publish(channel, message)
        print(f"Published to Redis {channel}: {message}")

    def subscribe(self, channel, callback):
        """Subscribe to a Redis channel and call the callback when a message is received."""
        def listener():
            self.pubsub.subscribe(channel)
            print(f"Subscribed to channel: {channel}")
            for message in self.pubsub.listen():
                if message['type'] == 'message':
                    callback(message['data'])
        
        listener_thread = threading.Thread(target=listener)
        listener_thread.daemon = True
        listener_thread.start()

    def close(self):
        """Close the Redis connection."""
        self.redis.close()
        print("Closed Redis connection.")
