# institutional_agent/llm_interface.py
"""
Handles all interactions with the external Large Language Model (LLM).
This module contains a suite of specialized functions, each with a prompt
engineered for a specific task within the simulation.
"""
import os
import json
import re
import time
import google.generativeai as genai
from dotenv import load_dotenv
from config import LLM_MODEL_NAME, LLM_MAX_RETRIES

# --- HELPER FUNCTION FOR ROBUST JSON PARSING ---
def _extract_json_from_llm_response(response_text):
    """Finds and extracts a JSON object or a list from a string."""
    match = re.search(r'[\{\[]', response_text)
    if not match: return None
    start_index = match.start()
    end_char = '}' if response_text[start_index] == '{' else ']'
    end_index = response_text.rfind(end_char)
    if end_index > start_index:
        json_text = response_text[start_index : end_index + 1]
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            return None
    return None

def _call_llm_with_retry(llm_client, prompt, function_name="LLM Call"):
    """
    A centralized, robust function to call the LLM with retry logic.
    Handles API errors and parsing issues gracefully.
    """
    for attempt in range(LLM_MAX_RETRIES):
        try:
            response = llm_client.generate_content(prompt)
            return response.text # Return the raw text on success
        except Exception as e:
            print(f"API Error in {function_name} (Attempt {attempt + 1}/{LLM_MAX_RETRIES}): {e}")
            if attempt < LLM_MAX_RETRIES - 1:
                time.sleep(2) # Wait a bit longer before retrying
            else:
                print(f"API Failure: All retries failed for {function_name}.")
                return None # Return None after all retries fail
    return None

# --- 0. Ecosystem SETUP ---

# institutional_agent/llm_interface.py

def generate_agent_profile_from_concept(llm_client, economy_type, agent_concept):
    """
    Takes a simple agent concept and asks the LLM to generate a complete,
    structured JSON profile for it with a strictly enforced status dictionary.
    """
    agent_id = agent_concept.get('agent_id', 'Unknown Agent')
    business_model = agent_concept.get('business_model', 'N/A')

    if economy_type == 'Linear':
        example_supply_chain = '{ "model_type": "linear", "material_mix": { "imported_wheat_flour": 1.0 } }'
    else: # Circular
        example_supply_chain = '{ "model_type": "circular", "material_mix": { "upcycled_sg_ingredients": 1.0 } }'

    # --- NEW: Define the non-negotiable status structure ---
    required_status_keys = """
    "cash_flow": 50, "short_term_debt_coverage": 50, "working_capital": 50,
    "profit_margin": 50, "market_share": 50, "revenue_consistency": 50,
    "roi": 50, "productivity": 50, "entry_into_new_market": 50,
    "brand_recognition": 50, "esg_performance": 50, "customer_satisfaction": 50,
    "vision_alignment_score": 50, "long_term_sustainability": 50
    """

    prompt = f"""
    You are a data entry specialist and economic modeler. Your task is to create a complete JSON data profile for a specific business entity.

    **Entity Details:**
    - **Agent ID:** "{agent_id}"
    - **Business Model:** "{business_model}"
    - **Overarching Economy:** "{economy_type}"

    **Instructions:**
    1.  Based on the entity details, create a single, complete JSON object.
    2.  The JSON object MUST contain these exact top-level keys: "agent_id", "vision_statement", "business_model", "supply_chain", and "initial_status".
    3.  The "supply_chain" value MUST be a nested JSON object structured exactly like this: {example_supply_chain}.
    4.  The "initial_status" value MUST be a nested JSON object. **It is CRITICAL that it contains ALL of the following keys with reasonable default numerical values:**
        {required_status_keys}
    5.  Your entire response MUST BE just the raw JSON object, starting with '{{' and ending with '}}'. Do not add any other text.
    """
    response_text = _call_llm_with_retry(llm_client, prompt, f"generate_profile_for_{agent_id}")
    if response_text:
        profile = _extract_json_from_llm_response(response_text)
        # Add a check for the crucial key
        if isinstance(profile, dict) and isinstance(profile.get("initial_status"), dict) and "profit_margin" in profile["initial_status"]:
            return profile
    print(f"LLM Failure: Could not generate a valid profile with all required status keys for concept '{agent_id}'.")
    return None

def generate_ecosystem_concepts_with_llm(llm_client, economy_type, core_business_model):
    """
    Asks the LLM to brainstorm a list of plausible agent CONCEPTS (name and business model only).
    This is the 'Ideation' step.
    """
    prompt = f"""
    You are an expert economic planner for Singapore. Your task is to brainstorm a list of 2 other essential entities that would exist in an economic ecosystem.

    **Core Economic Model:** A "{economy_type}" Economy.
    **Central Business Type:** "{core_business_model}"

    **Instructions:**
    1.  Brainstorm a list of agent concepts. This MUST include one **supplier** and one **government/regulatory body**.
    2.  For each concept, provide a JSON object with only two keys: "agent_id" and "business_model".
    3.  The concepts MUST align with the overarching **{economy_type}** model.
    4.  Respond with ONLY a Python-parseable list of these simple JSON objects. Your response MUST start with '[' and end with ']'.

    **Example Response for a 'Circular' bakery:**
    [
      {{
        "agent_id": "Okara_Upcycling_Coop",
        "business_model": "A co-operative that collects okara (soy pulp) from tofu producers and processes it into a high-protein flour for bakeries."
      }},
      {{
        "agent_id": "SFA_Circular_Grants_Office",
        "business_model": "A government agency under the Singapore Food Agency that provides grants and regulatory support for businesses using upcycled ingredients."
      }}
    ]
    """
    response_text = _call_llm_with_retry(llm_client, prompt, "generate_ecosystem_concepts")
    if response_text:
        concepts = _extract_json_from_llm_response(response_text)
        if isinstance(concepts, list):
            return concepts
    print("LLM Failure: Could not generate ecosystem concepts.")
    return []

# --- 1. CORE SETUP ---
def configure_llm():
    """Configures and returns the generative model client."""
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in .env file.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(LLM_MODEL_NAME)

# --- 2. INSTITUTIONAL AGENT - PERCEPTION & STRATEGY ---
def generate_strategies_from_llm(llm_client, lowest_need, profile_summary):
    """Generates high-level candidate strategies based on the agent's most critical need."""
    prompt = f"""
    You are the strategic planning unit for an institution.
    Profile: {profile_summary}
    Your most critical need right now is: '{lowest_need}'.

    Brainstorm a list of 2 high-level, actionable strategies to address this need.
    Respond with only a Python-parseable list of strings and nothing else.
    Example: ["Launch a cost-reduction initiative", "Seek new venture capital funding"]
    """
    response_text = _call_llm_with_retry(llm_client, prompt, "generate_strategies")
    if response_text:
        strategy_list = _extract_json_from_llm_response(response_text)
        if isinstance(strategy_list, list) and strategy_list:
            return strategy_list
    return [f"Generic strategy for {lowest_need} 1"]

def analyze_event_impact_with_llm(llm_client, agent_profile_summary, event_description, event_effect):
    """Asks the LLM to analyze an environmental event from the agent's perspective."""
    prompt = f"""
    You are the internal strategic analysis unit for an institution.

    Our Profile: {agent_profile_summary}

    An external event has just occurred:
    - Event Description: "{event_description}"
    - Direct Impact on Us: "Our '{event_effect['metric']}' changed by {event_effect['modifier']}."

    Instructions:
    1.  Analyze this event's implications for our organizational needs (e.g., survival, profitability, reputation).
    2.  Classify the event's primary impact on us as either "Threat" or "Opportunity". A "Threat" harms our needs, while an "Opportunity" helps them.
    3.  Provide a brief, one-sentence rationale for your classification.
    4.  Respond with ONLY a single, raw JSON object. Your response MUST start with '{{' and end with '}}'. Do not add any other text or formatting.

    Example Response:
    {{
      "impact_type": "Threat",
      "reasoning": "The new tax directly harms our profitability and survival needs by increasing costs."
    }}

    Now, provide the JSON object for the event described above.
    """
    response_text = _call_llm_with_retry(llm_client, prompt, "analyze_event_impact")
    if response_text:
        analysis = _extract_json_from_llm_response(response_text)
        if analysis and "impact_type" in analysis:
            return analysis
    return {"impact_type": "Neutral", "reasoning": "Impact could not be determined."}

# --- 3. INSTITUTIONAL AGENT - ACTION & DECISION MAKING ---
def decompose_strategy_into_actions(llm_client, strategy, agent_profile):
    """Takes a high-level strategy and breaks it down into projects relevant to a Singaporean bakery."""
    prompt = f"""
    You are the Chief Operating Officer for a Singapore-based bakery.

    Our Company Profile:
    - Vision: "{agent_profile.static_status['vision_statement']}"
    - Business Model: "{agent_profile.static_status['business_model']}"

    Your task is to take a high-level strategic objective and break it down into 2-3 specific, tangible projects that a real bakery in Singapore would execute.

    Strategic Objective: "{strategy}"

    Instructions:
    1.  Brainstorm concrete projects relevant to a bakery's operations (e.g., sourcing, production, energy, waste).
    2.  For each project, create a JSON object for our Life Cycle Assessment (LCA) system.
    3.  Your entire response MUST BE just a raw, valid, Python-parseable list of JSON objects, starting with '[' and ending with ']'. Do not add any other text.
    4.  The nested 'lca_message' object must have the keys "stage", "activity", "amount", and "unit".

    Example for the strategy "Improve resource efficiency":
    [
      {{
        "project_name": "Install new deck ovens with better heat retention",
        "rationale": "Reduces electricity consumption per bake cycle, lowering operational costs, our primary resource usage.",
        "lca_message": {{
          "stage": "capital_goods",
          "activity": "commercial_oven_manufacturing",
          "amount": 5,
          "unit": "ovens"
        }}
      }},
      {{
        "project_name": "Implement a water recycling system for washing equipment",
        "rationale": "Reduces water utility costs, a key concern in Singapore.",
        "lca_message": {{
          "stage": "infrastructure",
          "activity": "water_recycling_system_installation",
          "amount": 1,
          "unit": "system"
        }}
      }}
    ]

    Now, provide the list of JSON objects for our bakery based on the strategic objective.
    """
    response_text = _call_llm_with_retry(llm_client, prompt, "decompose_strategy")
    if response_text:
        action_list = _extract_json_from_llm_response(response_text)
        if isinstance(action_list, list):
            return action_list
    return []
    
def perform_crisis_triage_with_llm(llm_client, agent_profile, event_description, perceived_threat, current_lowest_need):
    """
    Acts as a crisis management team to decide if a perceived threat
    is critical enough to override the agent's normal operational focus.
    """
    prompt = f"""
    You are a crisis management team for a company. You must perform a triage.

    Our Company Profile:
    - Business Model: "{agent_profile.static_status['business_model']}"

    The Situation:
    - An external event occurred: "{event_description}"
    - Our initial analysis classifies this as a: "{perceived_threat['impact_type']}" with the reasoning: "{perceived_threat['reasoning']}"
    - Our current, normal priority was to address our lowest need: "{current_lowest_need}".

    Your Task:
    1.  Assess the severity of the threat. Is it an existential or critical risk that demands immediate, focused attention?
    2.  Decide between two courses of action: "Address Threat" or "Continue Normal Operations".
    3.  If you choose "Address Threat", you MUST define a new, single, urgent strategic objective to counter this specific threat.
    4.  If you choose "Continue Normal Operations", the urgent objective should be null.
    5.  Respond with ONLY a single, raw JSON object. Your response MUST start with '{{' and end with '}}'.

    Example Response (for a critical threat):
    {{
      "triage_decision": "Address Threat",
      "urgent_strategic_objective": "Immediately secure alternative supply chains and communicate transparently with stakeholders about delays."
    }}

    Example Response (for a non-critical threat):
    {{
      "triage_decision": "Continue Normal Operations",
      "urgent_strategic_objective": null
    }}

    Now, provide your triage decision for the situation described.
    """
    response_text = _call_llm_with_retry(llm_client, prompt, "perform_crisis_triage")
    if response_text:
        triage_result = _extract_json_from_llm_response(response_text)
        if triage_result and "triage_decision" in triage_result:
            return triage_result
    return {"triage_decision": "Continue Normal Operations", "urgent_strategic_objective": None}

def select_final_project_with_llm(llm_client, agent_profile, strategy, combined_project_list):
    """Acts as the CEO, making a final decision from a list of options."""
    project_list_str = json.dumps(combined_project_list, indent=2)
    prompt = f"""
    You are the CEO of a company. You must make a final, binding decision.

    Our Company Profile:
    - Business Model: "{agent_profile.static_status['business_model']}"
    - Vision: "{agent_profile.static_status['vision_statement']}"

    Our Strategic Goal: "{strategy}"
    Candidate Projects:
    {project_list_str}

    Instructions:
    1.  Evaluate all candidates based on a balance of strategic alignment, resource feasibility, and long-term sustainability.
    2.  Choose the SINGLE best project to execute right now.
    3.  Respond with ONLY the raw JSON object of your chosen project.
    4.  Your response MUST start with '{{' and end with '}}'. DO NOT add any other text or Markdown formatting like ```json.
    """
    response_text = _call_llm_with_retry(llm_client, prompt, "select_final_project")
    if response_text:
        chosen_project = _extract_json_from_llm_response(response_text)
        if chosen_project and "project_name" in chosen_project:
            return chosen_project
    return None

# --- 4. ECOLOGIST AGENT - CONSULTATION ---
def generate_eco_alternatives_with_llm(llm_client, agent_profile, strategy, initial_ideas):
    """Acts as an Industrial Ecologist consultant specializing in the Singapore Food & Beverage sector."""
    initial_ideas_str = json.dumps(initial_ideas, indent=2)
    prompt = f"""
    You are an expert in Industrial Ecology and Food Tech, providing advice to a Singaporean bakery.

    **Core Mandate:** Your advice must be informed by LCA principles to guide the bakery towards minimizing waste and optimizing resource usage. You must consider Singapore's unique context: import dependency, high operational costs, and the government's '30 by 30' food security goal.

    **Our Company Profile:**
    - Business Model: "{agent_profile.static_status['business_model']}"
    
    **Our Strategic Objective:** "{strategy}"

    **Our Team's Initial Ideas:**
    {initial_ideas_str}

    **Your Task:**
    1.  Analyze our initial ideas from a local, Singaporean value-chain perspective.
    2.  Brainstorm 1-2 NEW, more impactful alternatives based on established Industrial Ecology concepts (e.g., industrial symbiosis with local breweries, using insect protein, upcycling waste from other food producers).
    3.  Format your new ideas as a Python-parseable list of JSON objects, using the exact same structure as our initial ideas.
    4.  Your entire response MUST BE just the raw list, starting with '[' and ending with ']'.
    """
    response_text = _call_llm_with_retry(llm_client, prompt, "generate_eco_alternatives")
    if response_text:
        eco_alternatives = _extract_json_from_llm_response(response_text)
        if isinstance(eco_alternatives, list):
            return eco_alternatives
    return []


# --- 5. LCA Agent ---
# institutional_agent/llm_interface.py

def brainstorm_lifecycle_stages_with_llm(llm_client, project_name, context):
    """
    Step 1 of the chain: Asks the LLM to identify the key lifecycle stages
    and the main product flow for each stage.
    """
    context_str = json.dumps(context, indent=2)
    prompt = f"""
    You are a senior Life Cycle Assessment (LCA) practitioner. Your first task is to define the lifecycle model for a given scenario.

    **Project:** "{project_name}"
    **Context (Goal, Scope, Assumptions):**
    {context_str}

    **Instructions:**
    1.  Based on the project scope, identify the 2-4 key lifecycle stages that must be modeled (e.g., "Raw Material Production", "Transportation", "Waste Treatment").
    2.  For each stage, identify the single primary output product or service flow.
    3.  Respond with ONLY a single JSON object. It must have one key: "stages".
    4.  "stages" should be a list of objects, each with "stage_name" and "output_flow".

    **Example for "Manufacturing PET Bottles":**
    {{
      "stages": [
        {{ "stage_name": "PET Granulate Production", "output_flow": "PET granulate, virgin" }},
        {{ "stage_name": "PET Bottle Production", "output_flow": "Bottle, polyethylene terephthalate" }}
      ]
    }}
    """
    response_text = _call_llm_with_retry(llm_client, prompt, "brainstorm_lifecycle_stages")
    if response_text:
        concepts = _extract_json_from_llm_response(response_text)
        if isinstance(concepts, dict) and "stages" in concepts:
            return concepts
    print("LLM Failure: Could not brainstorm valid lifecycle stages.")
    return None

# institutional_agent/llm_interface.py

def quantify_lifecycle_stage_with_llm(llm_client, stage_name, output_flow, context):
    """
    Step 2 of the chain: Takes a single lifecycle stage and asks the LLM
    to create a quantified recipe, now WITH A RATIONALE FOR EACH FLOW.
    """
    context_str = json.dumps(context, indent=2)
    prompt = f"""
    You are a Life Cycle Assessment (LCA) data engineer. Your task is to create a detailed and justified process recipe for a single lifecycle stage.

    **Lifecycle Stage to Model:** "{stage_name}"
    **Main Output of this Stage:** "{output_flow}"
    **Overall Project Context (Goal, Scope, Assumptions):**
    {context_str}

    **Instructions:**
    1.  Based on the project context, create a plausible recipe for this stage.
    2.  For the output AND every single input, you MUST provide a "rationale" key.
    3.  The rationale must explain **why you chose this specific flow name** (e.g., "This is the most common virgin material for this process") and **how you estimated its amount** (e.g., "Based on the 1,610 kg total waste assumption"). This is the most critical instruction.
    4.  You MUST respond with a single JSON object with "name", "output", and "inputs" keys.
    5.  "output" must be an object with "flow_name", "amount", "unit", and "rationale".
    6.  "inputs" must be a list of objects, each with "flow_name", "amount", "unit", and "rationale".
    """
    response_text = _call_llm_with_retry(llm_client, prompt, f"quantify_stage_{stage_name}")
    if response_text:
        recipe = _extract_json_from_llm_response(response_text)
        if (isinstance(recipe, dict) and "inputs" in recipe and "output" in recipe and
                "rationale" in recipe["output"] and
                all("rationale" in item for item in recipe["inputs"])):
            return recipe
    print(f"LLM Failure: Could not generate a valid quantified recipe with rationales for stage '{stage_name}'.")
    return None

# def fetch_lca_data_from_llm(llm_client, stage, activity):
#     """
#     Asks the LLM to act as a researcher to find a specific emission factor online.
#     """
#     prompt = f"""
#     You are an expert Life Cycle Assessment (LCA) data analyst. Your task is to use your knowledge base (equivalent to searching online databases and reports) to find a specific carbon footprint value.

#     **Activity to Research:**
#     - **Stage:** "{stage}"
#     - **Activity:** "{activity}"

#     **Instructions:**
#     1.  Find a common, average emission factor for this specific activity.
#     2.  You MUST provide the result in a structured JSON format.
#     3.  Your entire response MUST BE just the raw JSON object, starting with '{{' and ending with '}}'. Do not add any other text or markdown.
#     4.  The JSON object must have these exact keys:
#         - "activity": The activity you researched.
#         - "emissions_per_unit": The numerical value of the emission factor.
#         - "emission_unit": The unit of the emission factor (e.g., "kg CO2e", "ton CO2e", "g CO2e"). BE AS SPECIFIC AS POSSIBLE.
#         - "input_unit": The functional unit for the emission factor (e.g., "ton", "kg", "unit", "vehicle", "ton-km").
#         - "source": A short reference for the data (e.g., "IPCC AR5", "Ecoinvent 3.8", "EPA GREET Model"). If unknown, state "General knowledge".

#     **Example Response for "steel production":**
#     {{
#       "activity": "steel_production",
#       "emissions_per_unit": 1.9,
#       "emission_unit": "ton CO2e",
#       "input_unit": "ton",
#       "source": "World Steel Association"
#     }}

#     Now, provide the JSON object for the requested activity.
#     """
    
#     # Use the robust retry logic we built before
#     response_text = _call_llm_with_retry(llm_client, prompt, "fetch_lca_data")
#     if response_text:
#         lca_data = _extract_json_from_llm_response(response_text)
#         if lca_data and "emissions_per_unit" in lca_data:
#             return lca_data
            
#     # Return None on failure so the agent knows the research was unsuccessful
#     return None

# def get_unit_conversion_factor(llm_client, from_unit, to_unit):
#     """
#     Asks the LLM for a numerical factor to convert from one unit to another.
#     e.g., from 'ton' to 'kg', the factor is 1000.
#     """
#     prompt = f"""
#     You are a scientific data conversion utility. Your only job is to provide a single numerical conversion factor.

#     Task: Provide the number you would MULTIPLY by to convert a value from '{from_unit}' to '{to_unit}'.
    
#     - If converting from 'ton' to 'kg', the answer is 1000.
#     - If converting from 'g' to 'kg', the answer is 0.001.
#     - If converting from 'item' or 'vehicle' to 'kg', provide the average mass of one '{from_unit}' in kilograms.
#     - If the units are incompatible or you cannot find a factor, respond with 'None'.

#     Respond with ONLY the numerical value or the word 'None'.
#     """
#     response_text = _call_llm_with_retry(llm_client, prompt, "get_unit_conversion")
#     if response_text:
#         try:
#             # Try to convert the response to a float
#             return float(response_text)
#         except (ValueError, TypeError):
#             # If it fails (e.g., the response is 'None' or other text), return None
#             print(f"Warning: Could not determine conversion factor from '{from_unit}' to '{to_unit}'.")
#             return None
#     return None

# llm_interface.py

def make_final_decision_with_lca_data(llm_client, agent_profile, project, lca_result):
    """
    Acts as a CEO making a final go/no-go decision based on a project's
    strategic fit and its calculated environmental impact.
    """
    lca_result_str = json.dumps(lca_result, indent=2)
    project_str = json.dumps(project, indent=2)
    
    prompt = f"""
    You are the CEO. You must make a final, binding GO/NO-GO decision on a project.

    **Our Company Profile:**
    - **Vision:** "{agent_profile.static_status['vision_statement']}"
    - **Current ESG Performance Score:** {agent_profile.dynamic_status['esg_performance']}

    **Proposed Project:**
    {project_str}

    **Scientific Environmental Impact Assessment (from openLCA):**
    {lca_result_str}

    **Instructions:**
    1.  Review the project and its scientifically calculated carbon footprint (`total_kg_co2e`).
    2.  Balance the project's strategic goals against our vision and current ESG score.
    3.  Make a final decision: "Approve" or "Reject".
    4.  Provide a brief, one-sentence rationale for your decision.
    5.  Respond with ONLY a single, raw JSON object with the keys "decision" and "reasoning".

    **Example Response:**
    {{
      "decision": "Approve",
      "reasoning": "Although the carbon footprint is non-zero, the strategic benefit of upgrading our ovens aligns with our long-term efficiency goals."
    }}
    """
    response_text = _call_llm_with_retry(llm_client, prompt, "make_final_decision")
    if response_text:
        decision = _extract_json_from_llm_response(response_text)
        if decision and "decision" in decision:
            return decision
    return {"decision": "Reject", "reasoning": "Could not make a confident decision due to a analysis error."}

# --- 6. REPORTING MODULE ---

def generate_summary_report_with_llm(llm_client, scenario_name, agent_id, business_model, initial_status_str, final_status_str, full_history_str, total_co2_str):
    """Asks the LLM to act as an analyst and generate a narrative summary of the simulation."""
    prompt = f"""
    You are a Senior Business Analyst and Sustainability Consultant. Your task is to write a concise executive summary of a business simulation.

    **INPUT DATA:**
    - **Scenario Name:** {scenario_name}
    - **Agent Analyzed:** {agent_id}
    - **Agent Business Model:** {business_model}
    - **Initial State:**
    {initial_status_str}
    - **Final State:**
    {final_status_str}
    - **Total Carbon Footprint:** {total_co2_str}
    - **Full Simulation Log:**
    {full_history_str}

    **INSTRUCTIONS:**
    Based on all the data provided, generate a final report with the following structure:

    **1. Overall Impact Assessment:**
       - Start with a single verdict: "The '{scenario_name}' scenario had a [Net Positive, Net Negative, or Mixed] impact on {agent_id}."
       - Provide a brief, high-level justification for this verdict.

    **2. Key Areas Affected:**
       - Identify the top 2-3 organizational needs (e.g., Survival, Profitability, Reputation) that were most significantly impacted.
       - For each area, cite the specific metrics that changed the most.

    **3. Analysis of Key Drivers:**
       - Explain *why* these changes occurred.
       - Reference specific environmental events and the agent's own actions to create a clear cause-and-effect narrative.

    **4. Environmental Impact:**
        - Summarize the agent's overall carbon footprint in a single sentence.
        - Highlight any particularly impactful actions or projects that contributed to this footprint.
    
    **5. Strategic Takeaway:**
       - Conclude with a single, actionable recommendation for the agent's leadership team.

    Write the report in a clear, professional, and analytical tone.
    """
    response_text = _call_llm_with_retry(llm_client, prompt, "generate_summary_report")
    if response_text:
        return response_text
    return "Error: Could not generate the final report due to an API failure."

def generate_data_driven_report_with_llm(llm_client, scenario_name, data_table, agent_list_a, agent_list_b):
    """
    Writes a data-intensive executive summary, including an analysis
    of the generated agents in each economy.
    """
    prompt = f"""
    You are a macro-level Economic Strategist and Sustainability Analyst for a global institution like the World Bank. Your task is to analyze a multi-agent simulation comparing two economic models.

    **SCENARIO:** {scenario_name}

    **QUANTITATIVE DATA SUMMARY:**
    {data_table}

    **PARTICIPATING AGENTS IN EACH ECONOMY:**

    **Economy A (Linear):**
    {agent_list_a}

    **Economy B (Circular):**
    {agent_list_b}

    ---
    **INSTRUCTIONS:**
    Write a compelling analysis for policymakers. You MUST use the data from ALL tables above to justify every point. Structure your report with these exact headings:

    **1. Macroeconomic Verdict:**
       - Declare the winning economic model.

    **2. Analysis of Systemic Resilience:**
       - Analyze *why* the winning economy was more resilient by referencing the specific final values for 'Profit Margin' and 'Cash Flow' from the quantitative table.

    **3. The Role of the Ecosystem:**
       - **Look at the agent lists.** Contrast the *types* of agents that were generated for each economy (e.g., 'Okara Upcycling Co-op' vs. 'Global Wheat Importer').
       - Explain how the nature of the ecosystem directly contributed to the resilience and outcomes shown in the data table.

    **4. The Economic Case for Sustainability:**
       - Compare the 'Total CO2 Footprint' and 'ESG Performance' values from the table.
       - Link the winning model's lower footprint to its more stable, localized, and innovative ecosystem of agents.

    **5. Policy Recommendation:**
       - Conclude with a powerful, one-sentence policy recommendation, justified by the quantitative outcomes and the qualitative differences in the generated economic ecosystems.
    """
    response_text = _call_llm_with_retry(llm_client, prompt, "generate_data_driven_report")
    if response_text:
        return response_text
    return "Error: Could not generate the final data-driven report due to an API failure."