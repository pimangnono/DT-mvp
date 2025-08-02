# environment.py
import json

class Environment:
    def __init__(self, scenario_path):
        """
        Initializes the Environment by loading a scenario file.
        """
        print(f"Loading scenario from: {scenario_path}")
        with open(scenario_path, 'r') as f:
            self.scenario = json.load(f)
        
        self.name = self.scenario['name']
        self.duration = self.scenario['duration_steps']
        self.current_step = 0
        
        # Initialize material prices from the scenario
        self.material_prices = self.scenario.get('material_prices', {}).get('initial', {}).copy()
        if self.material_prices:
            print(f"Initial Material Prices: {self.material_prices}")

    def update(self):
        """
        Updates the environment's internal time and returns a list of events
        that are scheduled to trigger in this step. It no longer contains any
        logic about how to process these events.
        """
        self.current_step += 1
        print(f"\n==================== ENVIRONMENT STEP {self.current_step} / {self.duration} ====================")
        
        triggered_events = []
        for event in self.scenario.get('timed_events', []):
            if event['trigger_step'] == self.current_step:
                triggered_events.append(event)
        
        return triggered_events