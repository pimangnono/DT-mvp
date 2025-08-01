# environment.py
"""
Manages the simulation environment, loading scenarios and applying
their effects to agents over time.
"""
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
        self.timed_events = self.scenario['timed_events']
        print(f"Scenario '{self.name}' loaded. Duration: {self.duration} steps.")

    def get_initial_modifiers(self):
        """Returns the initial global factors to apply to agents at startup."""
        return self.scenario.get('global_factors', {}).get('initial', {}).get('effects', {})

    def _apply_effects(self, agents, effects, event_description):
        """
        Applies effects and explicitly notifies the agents via their perceive_event method.
        """
        for effect in effects:
            modifier = effect['modifier']
            metric = effect['metric']
            
            # Identify which agents to apply the effect to
            target_agents = []
            if effect['target'] == 'all':
                target_agents = agents
            elif effect['target'] == 'all_conditional':
                target_agents = [
                    agent for agent in agents 
                    if agent.profile.dynamic_status[effect['condition_metric']] >= effect['condition_threshold']
                ]

            # Apply the effect and notify each targeted agent
            for agent in target_agents:
                # 1. Apply the effect directly to the agent's profile
                agent.profile.dynamic_status[metric] += modifier
                print(f"\n>> ENV_EFFECT on {agent.agent_id}: {metric} changed by {modifier}.")
                
                # 2. Command the agent to perceive what just happened
                agent.perceive_event(event_description, effect)

    def update(self, agents):
        """
        Updates the environment and returns a list of events that were triggered
        in this step.
        """
        self.current_step += 1
        print(f"\n==================== ENVIRONMENT STEP {self.current_step} / {self.duration} ====================")
        
        triggered_events = []
        for event in self.timed_events:
            if event['trigger_step'] == self.current_step:
                print(f"\n>> ENV_EVENT TRIGGERED: '{event['name']}' ({event['description']})")
                triggered_events.append(event)
                # Apply effects to all relevant agents
                for effect in event['effects']:
                    for agent in agents: # Simplified: apply to all agents for now
                         agent.profile.dynamic_status[effect['metric']] += effect['modifier']
                         print(f">> Applied effect to {agent.agent_id}: {effect['metric']} changed by {effect['modifier']}.")
        
        return triggered_events # Return the events that just happened