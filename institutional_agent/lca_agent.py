# institutional_agent/lca_agent.py
"""
The LCAAgent is a specialized service agent that uses an LLM to dynamically
calculate the carbon footprint of actions taken by other agents.
It caches results to improve performance and reduce costs.
focus on searching for data produced by Industrial Ecologist who use LCA to produce data in guiding production and consumption (full value chain) in order to minimize waste genereation and optimize resource usage/consumption
"""
from . import llm_interface # Use relative import

class LCAAgent:
    def __init__(self, llm_client):
        """
        Initializes the LCA Agent.

        Args:
            llm_client: The configured Google LLM client for making API calls.
        """
        self.agent_id = "LCA_Auditor_Agent"
        self.llm_client = llm_client
        self.total_footprint_kg_co2e = 0
        self.cache = {}  # Cache to store LCA data: {(stage, activity): data}
        print(f"Agent '{self.agent_id}' initialized with LLM and an empty cache.")

    def _get_emission_factor(self, stage, activity):
        """
        Retrieves emission factor data, using the cache first.
        If not in cache, it calls the LLM to fetch the data.
        """
        cache_key = (stage, activity)
        if cache_key in self.cache:
            print(f"LCA_Auditor: Found '{activity}' in cache. Using cached data.")
            return self.cache[cache_key]
        
        print(f"LCA_Auditor: '{activity}' not in cache. Querying LLM...")
        # Not in cache, so we call the LLM interface function
        lca_data = llm_interface.fetch_lca_data_from_llm(
            self.llm_client, stage, activity
        )
        
        # Store the new result in the cache for future use
        self.cache[cache_key] = lca_data
        print(f"LCA_Auditor: Received data from LLM and updated cache. Source: {lca_data.get('source')}")
        return lca_data

    def process_action_message(self, acting_agent_id, message):
        """
        Processes an action message, calculates footprint using dynamic data,
        and reports the results.
        """
        if not message:
            return
            
        print(f"\n--- {self.agent_id} received a message from {acting_agent_id} ---")
        print(f"Action details: {message}")

        stage = message.get("stage")
        activity = message.get("activity")
        amount = message.get("amount", 0)

        if not stage or not activity:
            print("Warning: Message is missing 'stage' or 'activity'. Cannot process.")
            return

        try:
            # This now dynamically fetches data (or uses cache)
            factor_data = self._get_emission_factor(stage, activity)
            
            unit = factor_data["unit"]
            emissions_per_unit = factor_data["emissions_kg_co2e_per_unit"]
            
            # Special handling for distribution (e.g., 'ton-km')
            if "km" in unit or "mi" in unit:
                distance = message.get("distance_km", 1)
                footprint = amount * distance * emissions_per_unit
            else:
                footprint = amount * emissions_per_unit
            
            print(f"Calculated Footprint: {footprint:,.2f} kg CO2e (Based on {emissions_per_unit} kg/{unit})")
            self.total_footprint_kg_co2e += footprint
            print(f"Total Simulation Footprint so far: {self.total_footprint_kg_co2e:,.2f} kg CO2e")

        except Exception as e:
            print(f"Error calculating footprint for message {message}: {e}")