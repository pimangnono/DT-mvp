# # This script initializes the necessary components and calls the LCAAgent's
# # main calculation method with a specific, hardcoded project to verify
# # the connection and calculation workflow with openLCA.
# # """
# # import json
# # from institutional_agent import llm_interface
# # from institutional_agent.lca_agent import LCAAgent

# # def run_lca_test():
# #     """
# #     Initializes and runs a single test of the LCAAgent.
# #     """
# #     print("--- [LCA AGENT STANDALONE TEST] ---")

# #     # 1. Initialize the LLM client (needed by the LCAAgent for mapping)
# #     print("\nStep 1: Initializing LLM client...")
# #     try:
# #         llm_client = llm_interface.configure_llm()
# #         print("LLM client initialized successfully.")
# #     except Exception as e:
# #         print(f"Failed to initialize LLM client: {e}")
# #         return

# #     # 2. Initialize the LCAAgent
# #     # This will test the connection to the openLCA IPC server.
# #     print("\nStep 2: Initializing LCAAgent and connecting to openLCA...")
# #     lca_agent = LCAAgent(llm_client=llm_client, ipc_port=8080)
    
# #     # Check if the connection was successful before proceeding
# #     if not lca_agent.client:
# #         print("\nTest Failed: LCAAgent could not connect to the openLCA server.")
# #         print("Please ensure openLCA is running and the IPC server is started from the 'Tools > Developer Tools' menu.")
# #         return
    
# #     print("LCAAgent initialized successfully.")

# #     # 3. Define the test project based on your input
# #     print("\nStep 3: Defining the test project...")
# #     test_project_name = "R&D and Pilot Production of Flour-Reduced Baked Goods"
# #     # The lca_message contains the quantifiable details for the calculation
# #     test_project_details = {
# #         "stage": "manufacturing",
# #         "activity": "bakery_production_pilot_run",
# #         "amount": 100, # e.g., a 100 kg pilot batch
# #         "unit": "kg"
# #     }
# #     print(f"  - Project Name: {test_project_name}")
# #     print(f"  - Project Details: {json.dumps(test_project_details)}")

# #     # 4. Run the LCA calculation
# #     print("\nStep 4: Calling the calculate_lca_for_project method...")
# #     lca_result = lca_agent.calculate_lca_for_project(
# #         project_name=test_project_name,
# #         project_details=test_project_details
# #     )

# #     # 5. Print the final result
# #     print("\nStep 5: Displaying the final formatted result...")
# #     if lca_result:
# #         print("\n--- [TEST COMPLETED SUCCESSFULLY] ---")
# #         print("Final JSON Result:")
# #         print(json.dumps(lca_result, indent=2))
# #         print("------------------------------------")
# #     else:
# #         print("\n--- [TEST FAILED] ---")
# #         print("The LCA calculation did not return a valid result.")
# #         print("-----------------------")


# # if __name__ == "__main__":
# #     # Before running, make sure your openLCA application is open
# #     # and you have started the IPC Server from the menu.
# #     run_lca_test()

# import olca_ipc as ipc
# import olca_schema as o

# client = ipc.Client(8080)
# print(f"Connected to openLCA IPC server on port 8080.")

# print(client.find(o.FlowProperty, "Mass"))

# test.py
"""
A standalone script to build and test the complete RAG (Retrieval-Augmented
Generation) pipeline for the LCAAgent.

Stage 1: Prepares the openLCA data by creating embeddings and storing them in a
         PGVector database for semantic search.
Stage 2: Simulates a request, uses the RAG pipeline to create a new process in
         openLCA, and runs a calculation.
"""
import json
import time
import pandas as pd
import numpy as np
import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer
import olca_ipc as ipc
import olca_schema as o

# --- Import your existing modules ---
from institutional_agent import llm_interface
from institutional_agent.lca_agent import LCAAgent # We'll borrow its methods

# --- Database Configuration ---
# IMPORTANT: Update these with your actual PostgreSQL connection details
DB_CONFIG = {
    "dbname": "lca_data",
    "user": "lca_user",
    "password": "lca_password",
    "host": "localhost", # Because we mapped the ports, 'localhost' is correct
    "port": "5432"
}

# --- Global Variables ---
MODEL = SentenceTransformer('all-MiniLM-L6-v2')

# ==============================================================================
# STAGE 1: openLCA PREPARATION (RAG Database Setup)
# ==============================================================================

def setup_pgvector_database(conn):
    """Creates the necessary table and extension in PostgreSQL."""
    with conn.cursor() as cur:
        print(" - Enabling PGVector extension...")
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        
        print(" - Creating 'flows' table...")
        # Get embedding dimension from the model
        embedding_dim = MODEL.get_sentence_embedding_dimension()
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS flows (
                id UUID PRIMARY KEY,
                name TEXT,
                name_embedding VECTOR({embedding_dim}),
                flow_type TEXT,
                location TEXT,
                category TEXT
            );
        """)
        conn.commit()

def populate_database_from_excel(conn, excel_path="flows.xlsx"):
    """Reads flows.xlsx, creates embeddings, and populates the PGVector DB."""
    try:
        df = pd.read_excel(excel_path)
        print(f"Loaded {len(df)} flows from {excel_path}.")
    except FileNotFoundError:
        print(f"FATAL: {excel_path} not found.")
        return

    with conn.cursor() as cur:
        # Check if data already exists to avoid re-populating
        cur.execute("SELECT COUNT(*) FROM flows;")
        if cur.fetchone()[0] > 0:
            print("Database is already populated. Skipping population.")
            return
            
        print("Populating database. This may take a few minutes...")
        
        # 1. Create the combined text for embedding
        df['combined_text'] = df['name'].fillna('') + ' | ' + df['location'].fillna('') + ' | ' + df['category'].fillna('')
        
        # 2. Generate embeddings
        print(" - Generating embeddings for all flows...")
        embeddings = MODEL.encode(df['combined_text'].tolist(), show_progress_bar=True)
        
        # 3. Insert data into the database
        print(" - Inserting data into PGVector table...")
        for index, row in df.iterrows():
            cur.execute(
                "INSERT INTO flows (id, name, name_embedding, flow_type, location, category) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    row['id'],
                    row['name'],
                    embeddings[index],
                    row['flow_type'],
                    row['location'],
                    row['category']
                )
            )
        conn.commit()
        print("Database population complete.")

def run_stage_1_preparation():
    """Executes the entire data preparation and database setup stage."""
    print("\n--- [STAGE 1: openLCA PREPARATION & RAG DATABASE SETUP] ---")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        register_vector(conn) # Register the vector type with the connection
        
        setup_pgvector_database(conn)
        populate_database_from_excel(conn)
        
        conn.close()
        print("--- [STAGE 1 COMPLETE] ---")
        return True
    except Exception as e:
        print(f"FATAL ERROR during Stage 1: {e}")
        return False

# ==============================================================================
# STAGE 2: openLCA SETUP & CALCULATION
# ==============================================================================

def semantic_search_for_flow(conn, flow_name: str):
    """Performs a semantic search in the PGVector DB to find the best flow ID."""
    with conn.cursor() as cur:
        query_embedding = MODEL.encode(flow_name)
        
        # The '<=>' operator is from PGVector and finds the cosine distance
        cur.execute(
            "SELECT id, name FROM flows ORDER BY name_embedding <=> %s LIMIT 1;",
            (query_embedding,)
        )
        result = cur.fetchone()
        if result:
            print(f"     - CONTEXT MATCH for '{flow_name}': Found '{result[1]}' (ID: {result[0]})")
            return str(result[0])
        else:
            print(f"     - WARNING: Semantic search could not find a match for flow '{flow_name}'.")
            return None


def run_stage_2_calculation(lca_agent, conn):
    """Executes the LCA calculation using a robust, multi-stage lifecycle generation."""
    print("\n--- [STAGE 2: openLCA SETUP & CALCULATION] ---")
    
    # --- Define Goal, Scope, and Functional Unit ---
    project_name = "Avoided Lifecycle of Disposable Plastic Cutlery"
    context = {
        "goal": "Calculate the environmental savings (avoided carbon footprint) of opting out of plastic cutlery in Singapore delivery services for one month.",
        "scope": "Cradle-to-grave analysis of the avoided lifecycle: from raw material extraction for polypropylene (PP) cutlery, to its transportation, to its end-of-life landfill.",
        "functional_unit": "The provision of cutlery for 230,000 food delivery orders over one month.",
        "assumptions": [
            "Total avoided sets: 230,000",
            "Average weight of a PP cutlery set: 7 grams",
            "Total weight of avoided PP waste: 230,000 sets * 7 g/set = 1,610,000 g = 1,610 kg",
            "End-of-life transport: 40 km via 16-ton truck"
        ]
    }
    
    # --- CORRECTED PRINTOUTS ---
    print("\n--- [LCA JOB DEFINITION] ---")
    print(json.dumps(context, indent=2))
    print("--------------------------\n")

    # --- "CHAIN OF THOUGHT" LIFECYCLE GENERATION ---
    # Step 2.1a: Brainstorm the lifecycle stages
    print("Step 2.1a: Brainstorming key lifecycle stages...")
    lifecycle_stages = llm_interface.brainstorm_lifecycle_stages_with_llm(
        lca_agent.llm_client, project_name, context
    )
    if not lifecycle_stages:
        print("Test Failed: Could not brainstorm lifecycle stages.")
        return

    # Step 2.1b: Quantify each stage to build the full recipe
    print("\nStep 2.1b: Quantifying each lifecycle stage...")
    full_recipe = {"processes": []}
    for stage in lifecycle_stages.get("stages", []):
        print(f"  - Quantifying stage: '{stage['stage_name']}'...")
        stage_recipe = llm_interface.quantify_lifecycle_stage_with_llm(
            lca_agent.llm_client, stage['stage_name'], stage['output_flow'], context
        )
        if stage_recipe:
            full_recipe["processes"].append(stage_recipe)
        time.sleep(2) # Pace the calls

    if not full_recipe["processes"]:
        print("Test Failed: Could not quantify any lifecycle stages.")
        return
    
    # The final process is the last one in the chain
    full_recipe["final_process_name"] = full_recipe["processes"][-1]["name"]

    print("\n--- [LLM-Generated Lifecycle Model] ---")
    print(json.dumps(full_recipe, indent=2))
    print("---------------------------------------\n")
    
    # --- Create Processes and Run Calculation in openLCA ---
    print("Step 2.2: Building temporary lifecycle processes in openLCA...")
    # This logic is now borrowed and adapted from the main LCAAgent
    temp_objects_to_delete = []
    try:
        # Map all required flows to their DB references first
        flow_refs = lca_agent._map_recipe_flows_to_refs(full_recipe)

        # Create a process for each stage in the recipe
        process_refs = {}
        for process_def in full_recipe['processes']:
            process = lca_agent._create_lca_process(process_def, flow_refs)
            if process:
                process_refs[process.name] = process.to_ref()
                temp_objects_to_delete.append(process.to_ref())
        
        final_process_ref = process_refs.get(full_recipe['final_process_name'])
        if not final_process_ref: raise ValueError("Final process not found in created processes.")
            
        print("\nStep 2.3: Creating product system and running calculation...")
        temp_system_ref = lca_agent.client.create_product_system(final_process_ref)
        temp_objects_to_delete.append(temp_system_ref)
        impact_method_ref = lca_agent._find_impact_method_ref()
        
        setup = o.CalculationSetup(target=temp_system_ref, impact_method=impact_method_ref)
        result = lca_agent.client.calculate(setup)
        result.wait_until_ready()
        
        inventory = result.get_total_impacts()
        formatted_result = lca_agent._format_result(inventory, project_name, full_recipe['final_process_name'])
        
        print("\n--- [STAGE 2 COMPLETE: CALCULATION SUCCESSFUL] ---")
        print("Final JSON Result:")
        print(json.dumps(formatted_result, indent=2))

    except Exception as e:
        print(f"Test Failed during calculation: {e}")
    finally:
        if lca_agent.client and temp_objects_to_delete:
            print(f"\nCleaning up {len(temp_objects_to_delete)} temporary objects from server...")
            for obj_ref in reversed(temp_objects_to_delete):
                lca_agent.client.delete(obj_ref)
    
    

# ==============================================================================
# MAIN ORCHESTRATOR
# ==============================================================================

def main():
    """Main function to run the test stages."""
    
    # --- Stage 1 ---
    if not run_stage_1_preparation():
        return # Stop if database setup fails

    # --- Stage 2 ---
    print("\nInitializing LCAAgent for Stage 2...")
    llm_client = llm_interface.configure_llm()
    lca_agent = LCAAgent(llm_client)
    
    if not lca_agent.client:
        print("Could not connect to openLCA. Aborting Stage 2.")
        return
        
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        register_vector(conn)
        run_stage_2_calculation(lca_agent, conn)
        conn.close()
    except Exception as e:
        print(f"A database error occurred during Stage 2: {e}")

if __name__ == "__main__":
    main()