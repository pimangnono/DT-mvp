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
    """Takes a high-level strategy and breaks it down into a list of projects."""
    prompt = f"""
    You are a Chief Operating Officer (COO) for a specific company.

    Our Company Profile:
    - Vision: "{agent_profile.static_status['vision_statement']}"
    - Business Model: "{agent_profile.static_status['business_model']}"

    Your task is to take a high-level strategic objective and break it down into a list of 2-3 specific, tangible projects that are RELEVANT TO OUR BUSINESS MODEL.

    Strategic Objective: "{strategy}"

    Instructions:
    1.  Brainstorm concrete projects that a company like ours would execute.
    2.  For each project, create a JSON object for our Life Cycle Assessment (LCA) system.
    3.  YOU MUST respond with ONLY a raw, valid, Python-parseable list of JSON objects.
    4.  DO NOT include any explanations, introductory text, or markdown formatting like ```json. Your entire response must start with '[' and end with ']'.

    Example Response for a software company with the strategy "Launch a resource efficiency program":
    [
      {{
        "project_name": "Upgrade Data Center Cooling to Liquid Immersion",
        "rationale": "Dramatically reduces electricity consumption (PUE), our primary resource usage.",
        "lca_message": {{
          "stage": "infrastructure",
          "activity": "data_center_retrofit",
          "amount": 500,
          "unit_hint": "servers"
        }}
      }},
      {{
        "project_name": "Implement a 'Work from Home' policy to reduce office energy footprint",
        "rationale": "Reduces commuter emissions and office energy/water consumption.",
        "lca_message": {{
          "stage": "operations",
          "activity": "policy_implementation",
          "amount": 1,
          "unit_hint": "policy"
        }}
      }}
    ]

    Now, provide the list of JSON objects for our company based on the strategic objective.
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
    """Acts as an Industrial Ecologist consultant."""
    initial_ideas_str = json.dumps(initial_ideas, indent=2)
    prompt = f"""
    You are an expert in Industrial Ecology. Your purpose is to provide data-driven guidance on sustainable production and consumption.

    **Core Mandate:** Your advice must be informed by data and principles from Life Cycle Assessments (LCA) to guide our company across its full value chain. The ultimate goals are to **minimize waste generation** and **optimize resource usage**.

    **Our Company Profile:**
    - Business Model: "{agent_profile.static_status['business_model']}"
    
    **Our Strategic Objective:** "{strategy}"

    **Our Team's Initial Ideas:**
    {initial_ideas_str}

    **Your Task:**
    1. Analyze our initial ideas from a systemic, full value-chain perspective.
    2. Brainstorm 1-2 NEW, more impactful alternatives based on established Industrial Ecology concepts (e.g., circular economy, industrial symbiosis, dematerialization, biomimicry).
    3. Format your new ideas as a Python-parseable list of JSON objects, using the exact same structure as our initial ideas.
    4. Your entire response MUST BE just the raw list, starting with '[' and ending with ']'.
    """
    response_text = _call_llm_with_retry(llm_client, prompt, "generate_eco_alternatives")
    if response_text:
        eco_alternatives = _extract_json_from_llm_response(response_text)
        if isinstance(eco_alternatives, list):
            return eco_alternatives
    return []


# --- 5. REPORTING MODULE ---

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

    **4. Strategic Takeaway:**
       - Conclude with a single, actionable recommendation for the agent's leadership team.

    Write the report in a clear, professional, and analytical tone.
    """
    response_text = _call_llm_with_retry(llm_client, prompt, "generate_summary_report")
    if response_text:
        return response_text
    return "Error: Could not generate the final report due to an API failure."