import redis


class PlanningService:
    def __init__(self, redis_host='localhost', redis_port=6379):
        # Connect to Redis
        self.redis_client = redis.StrictRedis(host=redis_host, port=redis_port, db=0)
        self.sessions = []

    def create_sessions(self):
        """
        Create sessions for elbow and wrist exercises with their respective goals.
        Publish the goals to Redis key '/redis/goals'.
        """
        # Define goals for elbow and wrist
        elbow_goals = [-25, -50, -75, -100, -125]  # Elbow pitch goals (degrees)
        wrist_goals = [30, -30]  # Wrist rotation goals (CW/CCW)

        # Dictionary to hold all session goals
        all_goals = {}

        # Create elbow sessions
        for i, goal in enumerate(elbow_goals):
            session_id = f"elbow_{i}"
            session = {
                'session_id': session_id,
                'exercise': 'elbow',
                'goal': goal,
                'status': 'in_progress'
            }
            self.sessions.append(session)
            all_goals[session_id] = goal  # Add to dictionary of goals
            print(f"Elbow Session {i} created with Pitch Goal: {goal}°")

        # Create wrist sessions
        for i, goal in enumerate(wrist_goals):
            session_id = f"wrist_{i}"
            session = {
                'session_id': session_id,
                'exercise': 'wrist',
                'goal': goal,
                'status': 'in_progress'
            }
            self.sessions.append(session)
            all_goals[session_id] = goal  # Add to dictionary of goals
            print(f"Wrist Session {i} created with Rotation Goal: {goal}°")

        # Publish all goals to Redis under the key '/redis/goals'
        self.redis_client.set('/redis/goals', str(all_goals))  # Store the dictionary of goals
        print("Goals published to Redis under '/redis/goals'")


# Example of how to use the PlanningService
if __name__ == "__main__":
    # Initialize PlanningService
    planning_service = PlanningService()

    # Step 1: Create the sessions
    planning_service.create_sessions()
