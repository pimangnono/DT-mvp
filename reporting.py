# reporting.py
"""
This module handles the generation of a final executive summary at the end of a simulation run.
"""
import json
from institutional_agent import llm_interface

def _prepare_data_for_report(agent, scenario_name, lca_auditor):
    """Gathers and formats all necessary data for the summary report."""
    
    # Extract initial and final states for comparison
    initial_status = agent.memory.history[0]['status']
    final_status = agent.profile.dynamic_status
    
    # Prettify the data into strings for the LLM prompt
    initial_status_str = json.dumps(initial_status, indent=2)
    final_status_str = json.dumps(final_status, indent=2)
    full_history_str = json.dumps(agent.memory.history, indent=2)
    total_co2_str = f"{lca_auditor.total_footprint_kg_co2e:,.2f} kg CO2e"

    return {
        "scenario_name": scenario_name,
        "agent_id": agent.agent_id,
        "business_model": agent.profile.static_status['business_model'],
        "initial_status_str": initial_status_str,
        "final_status_str": final_status_str,
        "full_history_str": full_history_str,
        "total_co2_str": total_co2_str
    }

def generate_final_report(agent, scenario_name, lca_auditor):
    """
    Orchestrates the creation of the final summary report by preparing data
    and calling the LLM interface.
    """
    print("\n\n----------------------------------------------------")
    print("--- GENERATING FINAL EXECUTIVE SUMMARY VIA LLM ---")
    print("----------------------------------------------------")
    
    # 1. Prepare all the data
    report_data = _prepare_data_for_report(agent, scenario_name, lca_auditor)
    
    # 2. Call the LLM to get the narrative analysis
    narrative_summary = llm_interface.generate_summary_report_with_llm(
        agent.llm_client,
        **report_data # Pass all prepared data as keyword arguments
    )
    
    # 3. Print the final, formatted report
    print(narrative_summary)
    print("----------------------------------------------------")
    print("--- END OF REPORT ---")
    print("----------------------------------------------------")