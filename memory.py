# memory.py
class Memory:
    def __init__(self, initial_status):
        # History is now a list of dictionaries, providing full context per step
        self.history = [{
            "step": 0,
            "status": initial_status.copy(),
            "action_taken": "Initialization",
            "log": ["Agent created."]
        }]

    def update_memory_with_action(self, new_status, action):
        """Adds the new status and the action that led to it."""
        current_step = self.history[-1]["step"] + 1
        self.history.append({
            "step": current_step,
            "status": new_status.copy(),
            "action_taken": action,
            "log": [] # Fresh log for the new step
        })
        print("Agent's memory updated with new status and action.")

    def add_log_entry(self, log_message):
        """Adds a perception or event log to the CURRENT step's history."""
        if self.history:
            self.history[-1]["log"].append(log_message)