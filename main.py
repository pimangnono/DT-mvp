# main.py
import json
from agent import InstitutionalAgent
from institutional_agent import llm_interface
from institutional_agent.lca_agent import LCAAgent
from institutional_agent.industrialEcologist_agent import IndustrialEcologistAgent
from environment import Environment
import reporting

def run_simulation(scenario_file):
    """Sets up and runs a simulation based on a scenario file."""
    print("--- DIGITAL TWIN SOCIETY SIMULATION ---")

    # 1. Initialize LLM and Environment (No changes needed)
    try:
        llm_client = llm_interface.configure_llm()
        environment = Environment(scenario_file)
    except Exception as e:
        print(f"Error during initialization: {e}")
        return

    # 2. Initialize Service Agents (No changes needed)
    # These are singleton services for the whole society.
    lca_auditor = LCAAgent(llm_client=llm_client)
    eco_advisor = IndustrialEcologistAgent(llm_client=llm_client)

    # 3. Load base agent profiles (No changes needed)
    profiles_path = 'institutional_agent/initial_profiles.json'
    try:
        with open(profiles_path, 'r') as f:
            profiles_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {profiles_path} not found.")
        return
        
    # --- MODIFICATION 1: AGENT CREATION LOOP ---
    # We now create an agent for every profile in the JSON file.
    agents = []
    initial_mods = environment.get_initial_modifiers()
    print(f"Found {len(profiles_data)} agent profiles to create...")
    for agent_data in profiles_data:
        agent = InstitutionalAgent(
            agent_id=agent_data["agent_id"],
            vision_statement=agent_data["vision_statement"],
            business_model=agent_data["business_model"],
            initial_status=agent_data["initial_status"],
            llm_client=llm_client,
            initial_modifiers=initial_mods
        )
        agents.append(agent)
    
    print(f"\n--- Starting Scenario: '{environment.name}' for {len(agents)} agents ---")

    # 5. Run simulation loop
    for step in range(environment.duration):
        print(f"\n\n<<<<<<<<<<<<<<<<< SCENARIO STEP {step + 1} >>>>>>>>>>>>>>>>>")
        
        # A) The environment updates and reports what happened
        triggered_events = environment.update(agents)
        
        # B) ALL agents perceive the events and then think and act
        for agent in agents:
            # The agent's thinking process now takes the events as input
            lca_message = agent.think_and_act(
                eco_consultant=eco_advisor,
                triggered_events=triggered_events # Pass the events to the agent
            )
            
            # C) The LCA auditor reacts to the final action
            if lca_message:
                lca_auditor.process_action_message(agent.agent_id, lca_message)
            

    print("\n\n--- SCENARIO COMPLETE ---")
    
    # --- Print final raw stats for all agents ---
    for agent in agents:
        print(f"\nFinal status for {agent.agent_id}: {agent.profile.dynamic_status}")
    
    # The LCA audit is for the entire simulation society
    print("\n--- GLOBAL LCA AUDIT SUMMARY ---")
    print(f"Total calculated carbon footprint across all agents: {lca_auditor.total_footprint_kg_co2e:,.2f} kg CO2e")

    # --- MODIFICATION 2: FINAL REPORTING LOOP ---
    # We now generate a separate, detailed report for each agent.
    for agent in agents:
        reporting.generate_final_report(
            agent=agent,
            scenario_name=environment.name,
            lca_auditor=lca_auditor
        )


if __name__ == '__main__':
    scenario_to_run = 'scenarios/wheat_price_rise.json'
    run_simulation(scenario_to_run)