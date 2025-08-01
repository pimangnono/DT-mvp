# institutional_agent/reasoning_engine.py
"""
Contains the core "thinking" components of the agent.
"""
import numpy as np
# Use relative import for modules in the same package
from . import llm_interface

class NeedsModel:
    """Represents and scores the organizational needs."""
    def __init__(self):
        self.needs = {
            "survival": {"cash_flow": 0.5, "short_term_debt_coverage": 0.5, "working_capital": 0.5},
            "profitability_stability": {"profit_margin": 0.5, "market_share": 0.5, "revenue_consistency": 0.5},
            "efficiency_growth": {"roi": 0.5, "productivity": 0.5, "entry_into_new_market": 0.5},
            "industry_leadership_reputation": {"brand_recognition": 0.5, "esg_performance": 0.5, "customer_satisfaction": 0.5},
            "societal_impact": {"vision_alignment_score": 0.5, "long_term_sustainability": 0.5}
        }
    
    def assess_lowest_need(self, current_status):
        """Updates needs scores and returns the category with the lowest average score."""
        for category, needs_items in self.needs.items():
            for need_name in needs_items:
                if need_name in current_status:
                    self.needs[category][need_name] = current_status[need_name] / 100.0
        
        average_scores = {cat: np.mean(list(vals.values())) for cat, vals in self.needs.items()}
        lowest_need_category = min(average_scores, key=average_scores.get)
        return lowest_need_category, average_scores[lowest_need_category]

class DecisionMakingModel:
    """
    Selects a high-level strategy to address the most critical need.
    The evaluation of specific actions happens later in the think_and_act loop.
    """
    def select_optimal_strategy(self, llm_client, lowest_need, profile):
        """
        Generates a list of potential high-level strategies and asks the LLM to
        pick the most appropriate one.
        """
        print(f"Generating candidate strategies for need: '{lowest_need}'")
        
        # Step 1: Generate candidate strategies via LLM.
        # We now use the function that we know exists.
        candidate_strategies = llm_interface.generate_strategies_from_llm(
            llm_client, lowest_need, profile.get_summary()
        )
        print(f"Generated Candidate Strategies: {candidate_strategies}")

        # Step 2: In our new architecture, the "evaluation" is simply choosing one.
        # A more advanced model could score them, but for now, we'll pick one,
        # as the *real* evaluation happens when choosing between specific projects.
        # We can simulate a simple selection. For robustness, we handle the case of an empty list.
        if not candidate_strategies:
            print("Warning: No strategies were generated. Defaulting to a generic action.")
            return "Take generic action to improve " + lowest_need
        
        # Let's just pick the first one generated for simplicity.
        # The complex choice logic is now in the think_and_act loop.
        optimal_strategy = candidate_strategies[0]
        
        return optimal_strategy