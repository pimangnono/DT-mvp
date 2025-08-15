# institutional_agent/lca_agent.py
"""
The LCAAgent (Definitive "Generative Process" Version).
This agent dynamically creates a multi-process lifecycle model in openLCA
based on an LLM-generated recipe, mimicking the official documentation's
successful workflow for maximum compatibility and accuracy.
"""
import olca_ipc as ipc
import olca_schema as o
import pandas as pd
from . import llm_interface
import time

class LCAAgent:
    def __init__(self, llm_client, ipc_port=8080):
        self.agent_id = "openLCA_Process_Engineer_Agent"
        self.llm_client = llm_client
        self.client = None
        self.total_footprint_kg_co2e = 0.0
        self.flows_db = None
        # ... (Semantic Search Engine Initialization is the same)
        
        try:
            # Simple, proven connection
            client = ipc.Client(ipc_port)
            # A simple check that doesn't crash
            if client.find(o.FlowProperty, "Mass") is None:
                raise ConnectionError("Could not find fundamental 'Mass' FlowProperty.")
            self.client = client
            print(f"Agent '{self.agent_id}' initialized and connected to openLCA (Generative Mode).")
        except Exception as e:
            print(f"FATAL ERROR: Could not connect to openLCA. {e}")

    def calculate_lca_for_project(self, project_name, project_details):
        if not self.client or self.flows_db is None:
            return None

        print(f"\n>> {self.agent_id} received calculation request for: '{project_name}'")

        # Keep track of all temporary objects we create to ensure cleanup
        temp_objects_to_delete = []
        try:
            # 1. Get a detailed, multi-stage recipe from the LLM
            print("   - Step 1: Generating a multi-stage lifecycle recipe...")
            recipe = llm_interface.generate_lifecycle_recipe_with_llm(self.llm_client, project_name, project_details)
            if not recipe: return {"error": "LLM failed to generate a lifecycle recipe."}
            self._print_recipe_summary(recipe)

            # 2. Find flow references for all ingredients in the recipe
            print("   - Step 2: Mapping recipe ingredients to database flows via semantic search...")
            flow_refs = self._map_recipe_flows_to_refs(recipe)

            # 3. Create a process for each stage in the recipe
            print(f"   - Step 3: Creating {len(recipe['processes'])} temporary processes in openLCA...")
            process_refs = {}
            for process_def in recipe['processes']:
                process = self._create_lca_process(process_def, flow_refs)
                if process:
                    process_refs[process.name] = process.to_ref()
                    temp_objects_to_delete.append(process.to_ref())
            
            # 4. Create a product system from the FINAL process
            final_process_ref = process_refs.get(recipe['final_process_name'])
            if not final_process_ref: return {"error": "Recipe was missing a final process."}
            
            print("   - Step 4: Creating a product system and auto-linking processes...")
            product_system_ref = self.client.create_product_system(final_process_ref)
            temp_objects_to_delete.append(product_system_ref)

            # 5. Find impact method and run calculation
            impact_method_ref = self._find_impact_method_ref()
            if not impact_method_ref: return {"error": "Could not find IPCC GWP 100a impact method."}

            print("   - Step 5: Setting up and running the calculation...")
            setup = o.CalculationSetup(target=product_system_ref, impact_method=impact_method_ref)
            result = self.client.calculate(setup)
            result.wait_until_ready()

            # 6. Format and return result
            inventory = result.get_total_impacts()
            self._print_raw_result(inventory)
            formatted_result = self._format_result(inventory, project_name, recipe['final_process_name'])
            self.total_footprint_kg_co2e += formatted_result.get("total_kg_co2e", 0)
            result.dispose()
            return formatted_result

        except Exception as e:
            print(f"An error occurred during the generative LCA calculation: {e}")
            return {"error": f"An unexpected error occurred: {e}"}
        
        finally:
            # CRITICAL: Clean up all temporary objects
            if self.client and temp_objects_to_delete:
                print(f"   - Step 6: Cleaning up {len(temp_objects_to_delete)} temporary objects from server...")
                for obj_ref in reversed(temp_objects_to_delete):
                    self.client.delete(obj_ref)

    def _map_recipe_flows_to_refs(self, recipe):
        """Takes a recipe and returns a dictionary mapping flow names to o.Ref objects."""
        flow_refs = {}
        all_flow_names = set()
        for process_def in recipe['processes']:
            all_flow_names.add(process_def['output']['flow_name'])
            for item in process_def['inputs']: all_flow_names.add(item['flow_name'])
        
        for name in all_flow_names:
            flow_refs[name] = self._find_flow_ref(name)
        return flow_refs
        
    # institutional_agent/lca_agent.py

    def _create_lca_process(self, process_def, flow_refs):
        """Creates a single o.Process object from a recipe definition, now with robust checks."""
        process = o.new_process(f"[Sim] {process_def['name']}")
        
        # --- ROBUSTNESS FIX ---
        # Quantitative Reference (Output)
        output_flow_name = process_def.get('output', {}).get('flow_name')
        if not output_flow_name:
            print(f"     - WARNING: Process definition '{process.name}' is missing an output flow name. Skipping process.")
            return None
            
        output_ref = flow_refs.get(output_flow_name)
        if not output_ref:
            # If the specific flow wasn't found in the DB, this process cannot be created.
            print(f"     - WARNING: Could not create process '{process.name}' because its output flow '{output_flow_name}' was not found in the database. Skipping.")
            return None
        
        qr = o.new_output(process, output_ref, process_def['output']['amount'])
        qr.is_quantitative_reference = True
        
        # Inputs
        for item in process_def.get('inputs', []):
            input_flow_name = item.get('flow_name')
            input_ref = flow_refs.get(input_flow_name)
            # We only add inputs that were successfully found.
            if input_ref:
                o.new_input(process, input_ref, item['amount'])
            else:
                print(f"     - INFO: Skipping input '{input_flow_name}' for process '{process.name}' as it was not found in the database.")
        
        self.client.put(process)
        return process

    def _find_flow_ref(self, flow_name):
        """Searches the in-memory pandas DataFrame for the best matching flow ID."""
        flow_name_lower = flow_name.lower()
        # A simple but effective search: find rows where the name contains the search term
        matches = self.flows_db[self.flows_db['name_lower'].str.contains(flow_name_lower, na=False)]
        
        if not matches.empty:
            best_match = matches.iloc[0] # Take the first match
            flow_type = o.RefType.PRODUCT_FLOW if best_match['flow_type'] == 'PRODUCT_FLOW' else o.RefType.ELEMENTARY_FLOW
            print(f"     - Mapped '{flow_name}' to DB flow '{best_match['name']}'")
            return o.Ref(id=best_match['id'], ref_type=flow_type)
        
        print(f"     - WARNING: Could not find a match for flow '{flow_name}' in flows.xlsx.")
        return None

    def _find_impact_method_ref(self):
        # This logic remains the same
        methods = self.client.get_descriptors("ImpactMethod")
        for method in methods:
            if "ipcc" in method.name.lower() and "gwp" in method.name.lower() and "100a" in method.name.lower():
                return method.to_ref()
        return None

    def _print_raw_result(self, inventory):
        """Prints the raw LCA result for validation."""
        print("\n   --- [Raw openLCA Result Received] ---")
        if inventory:
            print(f"   - Calculation successful. Found {len(inventory)} impact categories.")
            for impact in inventory[:5]: # Print the first 5
                cat_name = impact.impact_category.name
                amount = impact.value
                unit = impact.impact_category.ref_unit
                print(f"     - {cat_name}: {amount:.4f} {unit}")
            if len(inventory) > 5: print("     - ... (and more)")
        else:
            print("   - Calculation ran, but returned no impact results.")
        print("   -------------------------------------\n")

    def _format_result(self, inventory: list, project_name, process_name):
        """Formats the result from the inventory of impact values."""
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
            
        return {
            "activity_requested": project_name,
            "process_used": process_name,
            "total_kg_co2e": round(total_gwp, 2),
            "data_source": "openLCA/" + db_name
        }