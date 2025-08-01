# institutional_agent/industrial_ecologist_agent.py
from . import llm_interface

class IndustrialEcologistAgent:
    def __init__(self, llm_client):
        self.agent_id = "Eco_Advisor_Agent"
        self.llm_client = llm_client
        print(f"Agent '{self.agent_id}' initialized as an active consultant.")

    # --- THE KEY CHANGE IS HERE ---
    # The first argument is now the full 'institutional_agent' object.
    def generate_alternatives(self, institutional_agent, strategy, initial_ideas):
        """
        Receives a consultation request and returns a list of sustainable alternatives.
        """
        # We now correctly access the agent_id from the main agent object.
        print(f"\n>> {self.agent_id} received a consultation request from {institutional_agent.agent_id}.")
        print(f">> Analyzing strategy: '{strategy}'")

        # We pass the 'profile' component to the LLM, which is what it expects.
        alternatives = llm_interface.generate_eco_alternatives_with_llm(
            self.llm_client, institutional_agent.profile, strategy, initial_ideas
        )
        
        if alternatives:
            print(f">> {self.agent_id} is providing {len(alternatives)} new sustainable alternative(s).")
        else:
            print(f">> {self.agent_id} could not generate new alternatives for this case.")
            
        return alternatives