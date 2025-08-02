# agent.py
import numpy as np
import json
import time
from memory import Memory
from communication import Communication
from institutional_agent import llm_interface
from institutional_agent.agent_profile import Profile
from institutional_agent.reasoning_engine import NeedsModel, DecisionMakingModel
from supply_chain_model import SupplyChainModel

class InstitutionalAgent:
    def __init__(self, agent_id, vision_statement, business_model, initial_status, supply_chain_data, llm_client):
        self.agent_id = agent_id
        self.llm_client = llm_client
        self.profile = Profile(vision_statement, business_model, initial_status)
        self.memory = Memory(self.profile.dynamic_status)
        self.communication = Communication(self.agent_id)
        self.needs_model = NeedsModel()
        self.decision_model = DecisionMakingModel()
        
        # Initialize the agent's unique supply chain
        self.supply_chain = SupplyChainModel(
            model_type=supply_chain_data['model_type'],
            material_mix=supply_chain_data['material_mix']
        )
        self.communication.connect()
    
    def apply_carbon_tax(self, tax_rate_per_ton, lca_auditor):
        """
        Calculates the agent's carbon tax liability based on the economy's
        current emissions and applies the cost directly to the agent's cash flow.
        """
        # This is a systemic tax. A simple model assumes the burden is shared.
        # It's based on the *current* total emissions of the economy up to this point.
        total_economy_emissions_kg = lca_auditor.total_footprint_kg_co2e
        total_economy_emissions_tons = total_economy_emissions_kg / 1000.0
        
        # A simple model where this agent bears the full brunt of the current emissions.
        # In a true multi-agent sim, you'd divide this by the number of agents.
        # For our A/B test of single-agent economies, this is correct.
        agent_tax_liability = total_economy_emissions_tons * tax_rate_per_ton
        
        print(f">> TAX_EVENT for {self.agent_id}: Applying carbon tax. Cost: ${agent_tax_liability:,.2f}")
        
        # The cost directly impacts cash reserves. We assume cash_flow is a metric
        # where 1 point = $1000 or some other scale factor. Let's assume 1 point = $10k for impact.
        cash_flow_impact = agent_tax_liability / 10000.0
        
        self.profile.dynamic_status['cash_flow'] -= cash_flow_impact
        self.profile.dynamic_status['cash_flow'] = max(0, self.profile.dynamic_status['cash_flow']) # Prevent negative cash flow


    def update_financials_from_environment(self, material_prices):
        """Agent 'feels' the impact of the economy on its costs before making a decision."""
        cogs_modifier = self.supply_chain.calculate_cogs_modifier(material_prices)
        # Directly impact the profit margin based on material costs
        self.profile.dynamic_status['profit_margin'] += cogs_modifier
        print(f">> {self.agent_id} financials updated. COGS modifier to profit margin: {cogs_modifier:.2f}")

    def think_and_act(self, eco_consultant, triggered_events, material_prices):
        """
        Orchestrates a full, strategic thinking cycle that includes event perception,
        crisis triage, and conditional consultation before acting.
        """
        print(f"\n--- Agent '{self.agent_id}' starting thinking cycle ---")
        
        # === PHASE 0: FINANCIAL UPDATE ===
        # The agent first "feels" the direct economic impact of the current
        # environment (e.g., material costs) on its finances.
        self.update_financials_from_environment(material_prices)

        # This variable will hold the strategy the agent decides to pursue.
        effective_strategy = None
        
        # === PHASE 1: PERCEPTION & CRISIS TRIAGE ===
        # This phase only runs if an external event has actually occurred in this step.
        if triggered_events:
            # For simplicity, the agent reacts to the first event of the step.
            event = triggered_events[0]
            print(f">> {self.agent_id} PERCEIVING an event: {event['description']}")

            # Construct a descriptive dictionary for the LLM to analyze the event's impact.
            # This handles different event types gracefully.
            effect_for_perception = {"metric": "market_conditions", "modifier": "significant_change"}
            raw_effect = event['effects'][0]
            if raw_effect.get('type') == 'price_change':
                effect_for_perception = {
                    "metric": f"{raw_effect['material']}_price",
                    "modifier": f"{raw_effect['change_percent']}%"
                }
            elif raw_effect.get('type') == 'carbon_tax':
                 effect_for_perception = {
                    "metric": "operational_costs",
                    "modifier": f"increased due to new carbon tax of ${raw_effect.get('tax_rate_per_ton_co2e', 0)}/ton"
                }

            # Use the LLM to analyze and classify the event.
            perception = llm_interface.analyze_event_impact_with_llm(
                self.llm_client,
                self.profile.get_summary(),
                event['description'],
                effect_for_perception
            )
            
            self.memory.add_log_entry(f"Perceived Event: {event['description']}. Impact: {perception.get('impact_type')}.")
            print(f">> Perception Analysis: This is a '{perception.get('impact_type')}'.")
            
            # If the event is perceived as a threat, perform triage to see if it's a crisis.
            if perception.get('impact_type') == "Threat":
                current_lowest_need, _ = self.needs_model.assess_lowest_need(self.profile.dynamic_status)
                print(f">> Threat detected. Performing crisis triage. Normal priority would be '{current_lowest_need}'.")
                
                triage_result = llm_interface.perform_crisis_triage_with_llm(self.llm_client, self.profile, event['description'], perception, current_lowest_need)
                
                # If the triage result is to address the threat, override the normal strategy.
                if triage_result.get('triage_decision') == "Address Threat":
                    print(">> Triage Result: CRITICAL. Overriding normal operations to handle the threat.")
                    effective_strategy = triage_result.get('urgent_strategic_objective')
                else:
                    print(">> Triage Result: Threat is not critical. Continuing with normal operations.")
        
        # === PHASE 2: DEFAULT STRATEGY FORMULATION ===
        # If after the triage phase no urgent strategy has been set, proceed with business-as-usual.
        if not effective_strategy:
            lowest_need, _ = self.needs_model.assess_lowest_need(self.profile.dynamic_status)
            print(f"No crisis. Proceeding with normal priority: addressing need '{lowest_need}'.")
            effective_strategy = self.decision_model.select_optimal_strategy(self.llm_client, lowest_need, self.profile)

        print(f"Effective Strategy set to: '{effective_strategy}'")
        time.sleep(1)

        # === PHASE 3: ACTION DECOMPOSITION & CONDITIONAL CONSULTATION ===
        print("Decomposing strategy into specific projects...")
        internal_projects = llm_interface.decompose_strategy_into_actions(self.llm_client, effective_strategy, self.profile)
        if not internal_projects:
            print("Brainstorming failed. Aborting turn.")
            return None
        time.sleep(1)

        # This is the key logic separating the two economies.
        # The 'eco_consultant' will be 'None' for the Linear Economy agent.
        combined_project_list = internal_projects
        if eco_consultant:
            print("Engaging Industrial Ecologist for sustainable alternatives...")
            eco_alternatives = eco_consultant.generate_alternatives(self, effective_strategy, internal_projects)
            combined_project_list += eco_alternatives
        else:
            print("No Industrial Ecologist available. Proceeding with internal ideas only.")

        print(f"Synthesizing options. Total projects to consider: {len(combined_project_list)}")
        time.sleep(1)

        # === PHASE 4: FINAL DECISION & EXECUTION ===
        print("Making final, informed decision from all available options...")
        final_choice = llm_interface.select_final_project_with_llm(self.llm_client, self.profile, effective_strategy, combined_project_list)
        if not final_choice:
            print("Could not make a final decision. Aborting turn.")
            return None
        
        project_name = final_choice['project_name']
        lca_message_for_action = final_choice['lca_message']
        print(f"Final Action Chosen: '{project_name}'")
        
        action_feedback = self._take_action(project_name)
        self.profile.update_status(action_feedback)
        self.memory.update_memory_with_action(self.profile.dynamic_status, project_name)
        
        return lca_message_for_action

    def _take_action(self, project_name):
        print(f"Executing Project: {project_name}")
        self.communication.publish("agent/action", project_name)
        feedback = {"cash_flow": np.random.randint(-5, 6), "profit_margin": np.random.randint(-5, 6), "productivity": np.random.randint(-5, 6), "brand_recognition": np.random.randint(-5, 6), "customer_satisfaction": np.random.randint(-5, 6), "market_share": np.random.randint(-2, 3)}
        return feedback