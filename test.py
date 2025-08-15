# test.py
"""
A standalone script to test the robust, generative functionality of the LCAAgent.
This script acts as a simple client, trusting the LCAAgent to handle all of its
own internal setup, including database checks.
"""
import json
from institutional_agent import llm_interface
from institutional_agent.lca_agent import LCAAgent
import build_rag_database

def run_lca_test():
    """
    Initializes and runs a single, comprehensive test of the LCAAgent.
    """
    print("--- [LCA AGENT STANDALONE TEST] ---")

    # 1. Initialize the LLM client
    print("\nStep 1: Initializing LLM client...")
    llm_client = llm_interface.configure_llm()
    if not llm_client:
        print("Test Failed: Could not initialize LLM client.")
        return

    # 2. Initialize the LCAAgent
    # The agent's __init__ method now contains all the logic to check
    # for the RAG database and connect to openLCA.
    print("\nStep 2: Initializing LCAAgent...")
    lca_agent = LCAAgent(llm_client=llm_client)
    
    # The agent is now self-contained. It will handle its own database checks
    if not lca_agent.is_ready():
        print("\nTest Failed: LCAAgent did not initialize successfully.")
        print("This could be due to a failed connection to openLCA or the RAG database.")
        print("If the RAG database is not populated, please run 'python build_rag_database.py' first.")
        return
    
    # 3. Define the test case
    project_name = "Avoided Lifecycle of Disposable Plastic Cutlery"
    context = {
        "goal": "Calculate the environmental savings (avoided carbon footprint) of opting out of plastic cutlery in Singapore delivery services for one month.",
        "scope": "Cradle-to-grave analysis of the avoided lifecycle.",
        "functional_unit": "The provision of cutlery for 230,000 food delivery orders.",
        "assumptions": [
            "Total avoided sets: 230,000",
            "Average weight of a PP cutlery set: 7 grams",
            "Total weight of avoided PP waste: 1,610 kg",
            "End-of-life transport: 40 km via 16-ton truck"
        ]
    }
    
    print("\n--- [LCA JOB DEFINITION] ---")
    print(json.dumps(context, indent=2))
    print("--------------------------\n")

    # 4. Run the full generative LCA calculation
    print("Step 3: Calling the main 'calculate_lca_for_project' method...")
    lca_result = lca_agent.calculate_lca_for_project(
        project_name=project_name,
        project_details=context
    )

    # 5. Print the final result
    print("\n--- [FINAL TEST RESULT] ---")
    if lca_result and "error" not in lca_result:
        print("--- [TEST COMPLETED SUCCESSFULLY] ---")
        print("Final JSON Result:")
        print(json.dumps(lca_result, indent=2))
    elif lca_result and "error" in lca_result:
        print(f"--- [TEST FAILED WITH HANDLED ERROR] ---")
        print(f"LCA Agent returned an error: {lca_result['error']}")
    else:
        print(f"--- [TEST FAILED WITH UNEXPECTED ERROR] ---")
        print("The LCA calculation returned None or an invalid result.")
    print("--------------------------")

if __name__ == "__main__":
    run_lca_test()