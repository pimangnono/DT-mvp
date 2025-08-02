import json
from institutional_agent import llm_interface
from economy import Economy 
import reporting

def orchestrate_economy_comparison(scenario_file):
    """
    Sets up and runs two parallel, generative economy simulations (Linear vs. Circular)
    and generates a final comparative report.
    """
    print("--- ORCHESTRATING PARALLEL GENERATIVE ECONOMY SIMULATION ---")

    # 1. Initialize the shared LLM client
    llm_client = llm_interface.configure_llm()

    # 2. Load the "seed" agent profiles that will start each economy
    profiles_path = 'institutional_agent/initial_profiles.json'
    with open(profiles_path, 'r') as f:
        all_seed_profiles = json.load(f)

    # Filter seed profiles for each economy type
    linear_seed_profiles = [p for p in all_seed_profiles if p['supply_chain']['model_type'] == 'linear']
    circular_seed_profiles = [p for p in all_seed_profiles if p['supply_chain']['model_type'] == 'circular']

    if not linear_seed_profiles or not circular_seed_profiles:
        print("Error: Could not find 'seed' profiles for both 'linear' and 'circular' economy types.")
        return

    # 3. Create and Run the Linear Economy Simulation
    linear_economy = Economy(
        economy_type='Linear', 
        seed_agent_profiles=linear_seed_profiles, 
        scenario_file=scenario_file, 
        llm_client=llm_client
    )
    linear_economy.run()
    results_linear = linear_economy.get_aggregate_results()

    # 4. Create and Run the Circular Economy Simulation
    circular_economy = Economy(
        economy_type='Circular', 
        seed_agent_profiles=circular_seed_profiles, 
        scenario_file=scenario_file, 
        llm_client=llm_client
    )
    circular_economy.run()
    results_circular = circular_economy.get_aggregate_results()

    # 5. Generate the Final Comparative Report
    scenario_name = json.load(open(scenario_file))['name']
    reporting.generate_final_report(
        llm_client,
        scenario_name=scenario_name,
        results_a=results_linear,
        results_b=results_circular
    )

if __name__ == '__main__':
    scenario_to_run = 'scenarios/supply_chain_shock_scenario.json'
    orchestrate_economy_comparison(scenario_to_run)