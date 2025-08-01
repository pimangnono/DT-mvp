# agent.py
import numpy as np
import json
import time
from memory import Memory
from communication import Communication
from institutional_agent import llm_interface
from institutional_agent.profile import Profile
from institutional_agent.reasoning_engine import NeedsModel, DecisionMakingModel

class InstitutionalAgent:
    def __init__(self, agent_id, vision_statement, business_model, initial_status, llm_client, initial_modifiers={}):
        self.agent_id = agent_id
        self.llm_client = llm_client
        
        modified_status = initial_status.copy()
        if initial_modifiers:
            print(f"Applying initial environment modifiers to {agent_id}: {initial_modifiers}")
            for key, value in initial_modifiers.items():
                if key in modified_status:
                    modified_status[key] += value

        self.profile = Profile(vision_statement, business_model, modified_status)
        self.memory = Memory(self.profile.dynamic_status)
        self.communication = Communication(self.agent_id)
        self.needs_model = NeedsModel()
        self.decision_model = DecisionMakingModel()
        self.communication.connect()

    
    def think_and_act(self, eco_consultant, triggered_events):
        """
        A strategic thinking loop that includes event perception and crisis triage
        BEFORE deciding on a final course of action.
        """
        print(f"\n--- Agent '{self.agent_id}' starting thinking cycle ---")
        
        # === PHASE 1: PERCEPTION & TRIAGE ===
        effective_strategy = None
        if triggered_events:
            # For this MVP, agent reacts to the first event of the step
            event = triggered_events[0]
            print(f">> {self.agent_id} PERCEIVING an event: {event['description']}")
            
            # 1a. Analyze the event's impact
            perception = llm_interface.analyze_event_impact_with_llm(self.llm_client, self.profile.get_summary(), event['description'], event['effects'][0])
            self.memory.add_log_entry(f"Perceived Event: {event['description']}. Impact: {perception.get('impact_type')}. Rationale: {perception.get('reasoning')}")
            print(f">> Perception Analysis: This is a '{perception.get('impact_type')}'.")
            
            # 1b. If it's a threat, perform triage
            if perception.get('impact_type') == "Threat":
                current_lowest_need, _ = self.needs_model.assess_lowest_need(self.profile.dynamic_status)
                print(f">> Threat detected. Performing crisis triage. Normal priority would be '{current_lowest_need}'.")
                
                triage_result = llm_interface.perform_crisis_triage_with_llm(self.llm_client, self.profile, event['description'], perception, current_lowest_need)
                
                if triage_result.get('triage_decision') == "Address Threat":
                    print(">> Triage Result: CRITICAL. Overriding normal operations.")
                    effective_strategy = triage_result.get('urgent_strategic_objective')
                else:
                    print(">> Triage Result: Threat is not critical. Continuing with normal operations.")
        
        # === PHASE 2: NORMAL STRATEGY FORMULATION (if no crisis) ===
        if not effective_strategy:
            lowest_need, _ = self.needs_model.assess_lowest_need(self.profile.dynamic_status)
            print(f"No crisis. Proceeding with normal priority: addressing need '{lowest_need}'.")
            effective_strategy = self.decision_model.select_optimal_strategy(self.llm_client, lowest_need, self.profile)

        print(f"Effective Strategy set to: '{effective_strategy}'")
        time.sleep(1)

        # === PHASE 3: ACTION DECOMPOSITION & CONSULTATION (on the effective strategy) ===
        print("Decomposing strategy into specific projects...")
        internal_projects = llm_interface.decompose_strategy_into_actions(self.llm_client, effective_strategy, self.profile)
        if not internal_projects:
            print("Brainstorming failed. Aborting turn.")
            return None
        time.sleep(1)

        print("Engaging Industrial Ecologist for sustainable alternatives...")
        eco_alternatives = eco_consultant.generate_alternatives(self, effective_strategy, internal_projects)
        combined_project_list = internal_projects + eco_alternatives
        print(f"Synthesizing options. Total projects to consider: {len(combined_project_list)}")
        time.sleep(1)

        # === PHASE 4: FINAL DECISION & EXECUTION ===
        print("Making final, informed decision...")
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