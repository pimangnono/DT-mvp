# institutional_agent/lca_agent.py
from . import llm_interface

class LCAAgent:
    def __init__(self, llm_client):
        self.agent_id = "LCA_Auditor_Agent"
        self.llm_client = llm_client
        self.total_footprint_kg_co2e = 0
        self.cache = {}
        print(f"Agent '{self.agent_id}' initialized with advanced standardization logic.")

    def _get_standardized_emission_factor(self, stage, activity, target_functional_unit='kg'):
        """
        Retrieves and fully standardizes an emission factor to a target functional unit.
        This now handles both emission unit and functional unit conversion.
        """
        cache_key = (stage, activity, target_functional_unit)
        if cache_key in self.cache:
            print(f"LCA_Auditor: Found fully standardized data for '{activity}' in cache.")
            return self.cache[cache_key]

        print(f"LCA_Auditor: No standardized data for '{activity}' per '{target_functional_unit}'. Beginning research...")
        
        # 1. Fetch the raw LCA data for the activity
        raw_lca_data = llm_interface.fetch_lca_data_from_llm(self.llm_client, stage, activity)
        if not raw_lca_data:
            print(f"LCA_Auditor: Initial research for '{activity}' failed.")
            return None

        # 2. Standardize the EMISSION unit (e.g., convert 'ton CO2e' to 'kg CO2e')
        emissions_per_unit = raw_lca_data.get('emissions_per_unit', 0)
        emission_unit_str = raw_lca_data.get('emission_unit', 'kg co2e').lower()
        emission_factor = 1.0
        if "ton" in emission_unit_str: emission_factor = 1000.0
        elif "g" in emission_unit_str and "kg" not in emission_unit_str: emission_factor = 0.001
        standardized_emissions = emissions_per_unit * emission_factor
        
        # 3. Standardize the FUNCTIONAL unit (e.g., convert 'per ton' to 'per kg')
        original_functional_unit = raw_lca_data.get('input_unit', 'unit').lower()
        final_emissions_per_target_unit = standardized_emissions

        # If the original unit doesn't match our target, we need to ask the LLM for a conversion
        if original_functional_unit != target_functional_unit:
            print(f"LCA_Auditor: Functional unit mismatch ('{original_functional_unit}' vs target '{target_functional_unit}'). Requesting conversion factor...")
            conversion_factor = llm_interface.get_unit_conversion_factor(self.llm_client, original_functional_unit, target_functional_unit)
            
            if conversion_factor:
                # Example: If original is 'ton' and target is 'kg', conversion factor is 1000.
                # To get emissions per kg, we must DIVIDE emissions per ton by 1000.
                final_emissions_per_target_unit = standardized_emissions / conversion_factor
                print(f"LCA_Auditor: Conversion successful. Factor: {conversion_factor}.")
            else:
                print(f"LCA_Auditor: Could not get a conversion factor. Analysis for this item may be inaccurate.")
        
        # 4. Cache and return the fully standardized data
        final_data = {
            "standardized_footprint": final_emissions_per_target_unit,
            "standardized_unit": f"kg CO2e / {target_functional_unit}",
            "source": raw_lca_data.get('source', 'Unknown')
        }
        self.cache[cache_key] = final_data
        return final_data

    def process_action_message(self, message, acting_agent_id="Unknown"):
        if not message: return
        print(f"\n--- {self.agent_id} received a message from {acting_agent_id} ---")
        print(f"Action details: {message}")

        stage = message.get("stage")
        activity = message.get("activity")
        amount = message.get("amount", 0)
        # The agent's action message should specify the unit of the amount
        amount_unit = message.get("unit", "kg").lower() 

        if not stage or not activity: return

        try:
            # We always standardize to 'kg' for the functional unit for consistency
            standardized_data = self._get_standardized_emission_factor(stage, activity, target_functional_unit='kg')
            
            if not standardized_data:
                print("LCA_Auditor: Research failed. No footprint calculated.")
                return

            # If the amount from the action is not in kg, we must convert it first
            final_amount_in_kg = amount
            if amount_unit != 'kg':
                conversion_factor = llm_interface.get_unit_conversion_factor(self.llm_client, amount_unit, 'kg')
                if conversion_factor:
                    final_amount_in_kg = amount * conversion_factor
                else:
                    print(f"Warning: Could not convert amount from '{amount_unit}' to kg. Assuming 1:1.")
            
            emissions_per_kg = standardized_data.get("standardized_footprint", 0)
            footprint = final_amount_in_kg * emissions_per_kg
            
            print(f"LCA CALCULATION: {final_amount_in_kg:,.2f} kg * {emissions_per_kg:,.2f} (kg CO2e / kg) = {footprint:,.2f} kg CO2e")
            self.total_footprint_kg_co2e += footprint
            print(f"Total Simulation Footprint so far: {self.total_footprint_kg_co2e:,.2f} kg CO2e")
        except Exception as e:
            print(f"Error calculating footprint for message {message}: {e}")