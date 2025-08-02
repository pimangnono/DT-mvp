# institutional_agent/profile.py
"""
Contains the Profile class, which manages the agent's static and dynamic attributes.
"""
class Profile:
    """Holds the agent's static and dynamic attributes."""
    def __init__(self, vision_statement, business_model, initial_status):
        self.static_status = {
            "vision_statement": vision_statement,
            "business_model": business_model
        }
        self.dynamic_status = initial_status

    def update_status(self, feedback):
        """Updates the dynamic status based on action feedback."""
        print(f"Received feedback: {feedback}")
        for key, value_change in feedback.items():
            if key in self.dynamic_status:
                self.dynamic_status[key] += value_change
                self.dynamic_status[key] = min(max(self.dynamic_status[key], 0), 100)
        print(f"Updated agent status: {self.dynamic_status}")

    def get_summary(self):
        """Returns a string summary of the agent's profile."""
        return (f"Vision: {self.static_status['vision_statement']}. "
                f"Status: {self.dynamic_status}")