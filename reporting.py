# reporting.py
import json
from institutional_agent import llm_interface

def _build_agent_list_table(agent_profiles, economy_type):
    """Creates a markdown table listing the agents in an economy."""
    header = f"| Agents in the {economy_type} Economy | Business Model |"
    separator = "|----------------------------------------|----------------------------------------------------------------------|"
    rows = [header, separator]

    if not agent_profiles:
        rows.append("| No agents were successfully created.   |                                                                      |")
        return "\n".join(rows)

    for profile in agent_profiles:
        agent_id = profile.get('agent_id', 'Unknown Agent')
        business_model = profile.get('business_model', 'N/A')
        # Truncate long business models for table neatness
        if len(business_model) > 68:
            business_model = business_model[:65] + "..."
        row = f"| {agent_id:<38} | {business_model:<68} |"
        rows.append(row)
    
    return "\n".join(rows)

def _build_comparison_table(results_a, results_b):
    """Creates a formatted markdown table from the simulation results."""
    status_a = json.loads(results_a.get('aggregate_final_status', '{}'))
    status_b = json.loads(results_b.get('aggregate_final_status', '{}'))
    header = "| Metric                    | {a_type} Economy      | {b_type} Economy       | Change     |".format(
        a_type=results_a.get('economy_type', 'A'), b_type=results_b.get('economy_type', 'B')
    )
    separator = "|---------------------------|-----------------------|------------------------|------------|"
    rows = [header, separator]
    metrics = ['profit_margin', 'cash_flow', 'esg_performance', 'market_share']
    for metric in metrics:
        val_a = float(status_a.get(metric, 0))
        val_b = float(status_b.get(metric, 0))
        change = val_b - val_a
        change_str = f"+{change:.2f}" if change >= 0 else f"{change:.2f}"
        row = "| {metric:<25} | {val_a:<21.2f} | {val_b:<22.2f} | {change_str:<10} |".format(
            metric=metric.replace('_', ' ').title(), val_a=val_a, val_b=val_b, change_str=change_str
        )
        rows.append(row)
    co2_a_str = results_a.get('total_co2', '0 kg CO2e')
    co2_b_str = results_b.get('total_co2', '0 kg CO2e')
    rows.append("| Total CO2 Footprint       | {a:<21} | {b:<22} |            |".format(a=co2_a_str, b=co2_b_str))
    return "\n".join(rows)

def generate_final_report(llm_client, scenario_name, results_a, results_b):
    """
    Orchestrates the creation of the final data-intensive summary report,
    including the list of generated agents.
    """
    print("\n\n========================================================")
    print("--- GENERATING FINAL COMPARATIVE ECONOMY ANALYSIS ---")
    print("========================================================")
    
    comparison_table = _build_comparison_table(results_a, results_b)
    agent_list_a = _build_agent_list_table(results_a.get('agent_profiles', []), results_a.get('economy_type'))
    agent_list_b = _build_agent_list_table(results_b.get('agent_profiles', []), results_b.get('economy_type'))
    
    narrative_summary = llm_interface.generate_data_driven_report_with_llm(
        llm_client,
        scenario_name=scenario_name,
        data_table=comparison_table,
        agent_list_a=agent_list_a,
        agent_list_b=agent_list_b
    )
    
    print(f"\n## Final Report: {scenario_name}\n")
    print("### Quantitative Performance Comparison\n")
    print(comparison_table)
    print("\n### Generated Economic Actors\n")
    print(agent_list_a)
    print("\n")
    print(agent_list_b)
    print("\n---\n")
    print("### Narrative Analysis\n")
    print(narrative_summary)
    print("\n========================================================")
    print("--- END OF REPORT ---")
    print("========================================================")