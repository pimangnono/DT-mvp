# institutional_agent/lca_agent.py
"""
The LCAAgent (Definitive PGVector Version). This agent uses the PGVector
database for intelligent, context-based semantic search. It includes a
robust check to ensure the RAG database is initialized before operating.
"""
import olca_ipc as ipc
import olca_schema as o
import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer
from . import llm_interface
import time
import json

# --- This must match test.py and docker-compose.yml ---
DB_CONFIG = {
    "dbname": "lca_data",
    "user": "lca_user",
    "password": "lca_password",
    "host": "localhost",
    "port": "5432"
}

class LCAAgent:
    def __init__(self, llm_client, ipc_port=8080):
        self.agent_id = "openLCA_Process_Engineer_Agent"
        self.llm_client = llm_client
        self.client = None
        self.total_footprint_kg_co2e = 0.0
        self.db_conn = None
        self.embedding_model = None
        self._is_ready = False

        try:
            # Initialize Semantic Engine
            print("Initializing Semantic Search Engine for LCA Agent...")
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            self.db_conn = psycopg2.connect(**DB_CONFIG)
            register_vector(self.db_conn)
            if not self._is_db_populated():
                raise ConnectionError("RAG database is not populated. Please run 'build_rag_database.py' first.")
            print("Semantic Search Engine initialized successfully (PGVector).")

            
            client = ipc.Client(ipc_port)
            
            if client is None:
                raise ConnectionError("Server did not respond to get_descriptors for ProductSystem.")
            
            self.client = client
            print(f"Agent '{self.agent_id}' initialized and successfully connected to openLCA.")
            self._is_ready = True

        except Exception as e:
            print(f"FATAL ERROR during LCAAgent initialization: {e}")
            if self.db_conn: self.db_conn.close()

    def is_ready(self):
        return self._is_ready

    def _is_db_populated(self):
        """Checks if the 'flows' table exists and has data."""
        if not self.db_conn:
            return False
        with self.db_conn.cursor() as cur:
            cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'flows');")
            if not cur.fetchone()[0]: return False
            cur.execute("SELECT COUNT(*) FROM flows;")
            if cur.fetchone()[0] > 0: return True
        return False

    def calculate_lca_for_project(self, project_name, project_details):
        if not self.is_ready():
            return None

        print(f"\n>> {self.agent_id} received calculation request for: '{project_name}'")
        temp_objects_to_delete = []
        try:
            # Use the robust, two-step "Chain of Thought" recipe generation
            
            # Step 1a: Brainstorm the lifecycle stages
            print("   - Step 1a: Brainstorming key lifecycle stages...")
            lifecycle_stages = llm_interface.brainstorm_lifecycle_stages_with_llm(
                self.llm_client, project_name, project_details
            )
            if not lifecycle_stages:
                return {"error": "LLM failed to brainstorm lifecycle stages."}

            # Step 1b: Quantify each stage to build the full recipe
            print("   - Step 1b: Quantifying each lifecycle stage...")
            full_recipe = {"processes": []}
            for stage in lifecycle_stages.get("stages", []):
                stage_recipe = llm_interface.quantify_lifecycle_stage_with_llm(
                    self.llm_client, stage['stage_name'], stage['output_flow'], project_details
                )
                if stage_recipe:
                    full_recipe["processes"].append(stage_recipe)
                time.sleep(2) # Pace the calls
            
            if not full_recipe["processes"]:
                return {"error": "LLM failed to quantify any lifecycle stages."}
            
            full_recipe["final_process_name"] = full_recipe["processes"][-1]["name"]
            # --- [END OF FIX] ---

            self._print_recipe_summary(full_recipe)
            
            flow_refs = self._map_recipe_flows_to_refs(full_recipe)
            process_refs = {}
            for process_def in full_recipe.get('processes', []):
                # We need the original name from the recipe to use as a key
                original_process_name = process_def.get('name')
                if not original_process_name:
                    continue # Skip malformed process definitions

                process = self._create_lca_process(process_def, flow_refs)
                if process:
                    process_ref = process.to_ref()
                    process_refs[original_process_name] = process_ref
                    temp_objects_to_delete.append(process_ref)

            # Now this lookup will work correctly
            final_process_name = full_recipe.get('final_process_name')

            process_id_string = process_refs.get(final_process_name) 
            if not process_id_string:
                return {"error": f"Crucial final process '{final_process_name}' could not be built."}
            
            final_process_ref = o.Ref(ref_type=o.RefType.Process, id=process_id_string) 
            print("   - Creating a product system and auto-linking processes...")
            
            temp_system_ref = self.client.create_product_system(final_process_ref)
            if not temp_system_ref:
                return {"error": "Failed to create product system."}
            temp_objects_to_delete.append(temp_system_ref)

            impact_method_ref = self._find_impact_method_ref()
            if not impact_method_ref: return {"error": "Could not find IPCC GWP 100a impact method."}

            print("   - Setting up and running the calculation...")
            setup = o.CalculationSetup(target=temp_system_ref, impact_method=impact_method_ref)
            result = self.client.calculate(setup)
            result.wait_until_ready()
            
            inventory = result.get_total_impacts()
            self._print_raw_result(inventory)
            formatted_result = self._format_result(inventory, project_name, final_process_name)
            self.total_footprint_kg_co2e += formatted_result.get("total_kg_co2e", 0)
            result.dispose()
            return formatted_result
        except Exception as e:
            print(f"An error occurred during the generative LCA calculation: {e}")
            return {"error": f"An unexpected error occurred: {e}"}
        finally:
            if self.client and temp_objects_to_delete:
                print(f"   - Cleaning up {len(temp_objects_to_delete)} temporary objects from server...")
                for obj_ref in reversed(temp_objects_to_delete):
                    self.client.delete(obj_ref)

    def _map_recipe_flows_to_refs(self, recipe):
        """
        Takes a recipe and returns a dictionary mapping flow names to o.Ref objects.
        This version is more robust in parsing the recipe structure.
        """
        flow_refs = {}
        all_flow_names = set()
        
        # Defensively gather all flow names
        if isinstance(recipe.get('processes'), list):
            for process_def in recipe['processes']:
                if isinstance(process_def, dict):
                    if isinstance(process_def.get('output'), dict):
                        all_flow_names.add(process_def['output'].get('flow_name'))
                    if isinstance(process_def.get('inputs'), list):
                        for item in process_def['inputs']:
                            if isinstance(item, dict):
                                all_flow_names.add(item.get('flow_name'))

        all_flow_names.discard(None) # Remove any None values from malformed recipes
        
        print(f"\n   - Mapping {len(all_flow_names)} unique recipe ingredients to database flows via semantic search...")
        for name in sorted(list(all_flow_names)): # Sorting makes the log predictable
            flow_refs[name] = self._find_flow_ref_with_pgvector(name)
        
        print("   - Mapping complete.")
        return flow_refs
        

    def _create_lca_process(self, process_def, flow_refs):
        """
        Creates a single o.Process object, now with enhanced logging to
        clearly show which flows were found and which were not.
        """
        process_name = process_def.get('name')
        output_def = process_def.get('output')
        if not process_name or not isinstance(output_def, dict):
            print("     - WARNING: Skipping malformed process definition from LLM.")
            return None

        print(f"\n   - Building Process: '{process_name}'")
        process = o.new_process(f"[Sim] {process_name}")
        
        # Output (Quantitative Reference) - this is mandatory
        output_flow_name = output_def.get('flow_name')
        output_ref = flow_refs.get(output_flow_name)
        
        # --- ENHANCED LOGGING ---
        if output_ref:
            print(f"     - [OK] Output flow '{output_flow_name}' found in DB.")
        else:
            print(f"     - [FAIL] CRITICAL: Output flow '{output_flow_name}' not found in DB. Process cannot be created.")
            return None
        
        qr = o.new_output(process, output_ref, output_def.get('amount', 1.0))
        qr.is_quantitative_reference = True
        
        # Inputs - these are optional
        print("     - Checking inputs...")
        for item in process_def.get('inputs', []):
            if not isinstance(item, dict): continue
            input_flow_name = item.get('flow_name')
            input_ref = flow_refs.get(input_flow_name)
            
            # --- ENHANCED LOGGING ---
            if input_ref:
                print(f"       - [OK] Input flow '{input_flow_name}' found in DB.")
                o.new_input(process, input_ref, item.get('amount', 0.0))
            else:
                print(f"       - [FAIL] INFO: Input '{input_flow_name}' not found in DB. It will be SKIPPED.")
        
        print(f"   - Uploading temporary process '{process.name}'...")
        self.client.put(process)
        return process

    def _find_flow_ref_with_pgvector(self, flow_name: str):
        if not self.db_conn or not self.embedding_model or not isinstance(flow_name, str):
            return None
        try:
            with self.db_conn.cursor() as cur:
                query_embedding = self.embedding_model.encode(flow_name)
                cur.execute("SELECT id, name, flow_type FROM flows ORDER BY name_embedding <=> %s LIMIT 1;", (query_embedding,))
                result = cur.fetchone()
                if result:
                    flow_id, flow_name_match, flow_type_str = result
                    print(f"     - CONTEXT MATCH for '{flow_name}': Found '{flow_name_match}' in DB")
                    # Use the schema Enum, which is correct for creating a Ref object
                    
                    ref_type_enum = o.RefType.Flow
                    return o.Ref(id=str(flow_id), ref_type=ref_type_enum)
                else:
                    print(f"     - SEARCH FAILED: No match found for '{flow_name}'.")
                    return None
        except Exception as e:
            print(f"     - ERROR during PGVector search for '{flow_name}': {e}")
            return None
            
    def _find_impact_method_ref(self):
        """Finds the impact method reference using the get_descriptors method with a RAW STRING."""
        methods = self.client.get_descriptors(o.ImpactMethod)
        for method in methods:
            if  method.name.lower() == "ipcc 2013":
                print(f"   - Found Impact Method: '{method.name}'")
                return method.to_ref().id
        return None

    def _print_raw_result(self, inventory):
        print("\n   --- [Raw openLCA Result Received] ---")
        if inventory:
            print(f"   - Calculation successful. Found {len(inventory)} impact categories.")
            for impact in inventory[:5]:
                cat_name = impact.impact_category.name
                amount = impact.value
                unit = impact.impact_category.ref_unit
                print(f"     - {cat_name}: {amount:.4f} {unit}")
            if len(inventory) > 5: print("     - ... (and more)")
        else:
            print("   - Calculation ran, but returned no impact results.")
        print("   -------------------------------------\n")
    
    def _format_result(self, inventory: list, project_name, process_name):
        total_gwp = 0.0
        if inventory:
            for impact in inventory:
                if "gwp" in impact.impact_category.name.lower():
                    total_gwp = impact.value
                    break
        try:
            db_name = self.client.get_database().name if self.client.get_database() else "default"
        except:
            db_name = "default"
        return { "activity_requested": project_name, "process_used": process_name, "total_kg_co2e": round(total_gwp, 2), "data_source": "openLCA/" + db_name }

    def _print_recipe_summary(self, recipe):
        print("\n--- [LLM-Generated Lifecycle Model] ---")
        print(json.dumps(recipe, indent=2))
        print("---------------------------------------\n")