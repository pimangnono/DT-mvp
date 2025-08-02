**Architectural Overview**

**Core Components**


1. main.py (The Orchestrator): The top-level entry point. It doesn't contain any simulation logic. Its sole responsibility is to initialize the shared LLM client, load "seed" profiles, and command two Economy objects to run their simulations before triggering the final report.
2. economy.py (The Sandbox): A self-contained "universe" that holds one entire simulation. It creates its own independent Environment, LCAAgent, and (conditionally) its IndustrialEcologistAgent. Its most important feature is the Genesis Phase, where it uses the LLM to procedurally generate a network of agents based on its economic type (Linear/Circular).
3. agent.py (The Cognitive Entity): Defines the InstitutionalAgent class. This is the primary actor in the simulation, equipped with a complex, multi-stage thinking process (think_and_act) that allows it to perceive, reason, and act with strategic intent.
4. institutional_agent/ (Agent's "Brain" and "DNA"): This package contains the core components that define an agent's identity and intelligence.

4-1. llm_interface.py: A critical module that acts as the "phone system" to the LLM. It contains a library of highly specific, engineered prompts that enable the agents to perform their various cognitive tasks (analysis, brainstorming, decision-making, etc.).
  
4-2. agent_profile.py: A simple class that holds an agent's static and dynamic status.
  
4-3. reasoning_engine.py: Contains the agent's NeedsModel, allowing it to identify its most urgent internal priority.
  
4-4. initial_profiles.json: A data file containing the "seed" agents that kickstart the Genesis Phase for each economy.
5. environment.py (The World State): A passive state manager. It loads a scenario from a JSON file, keeps track of the simulation's clock, and manages global variables like material prices. It is "dumb" by design, only reporting which events are scheduled for the current step.
6. event_handlers.py (The Rulebook): A completely decoupled module that contains the logic for what to do when an event occurs. It maps event type strings from the scenario files to specific Python functions (handle_price_change, handle_carbon_tax), making the system incredibly easy to extend with new events.
7. scenarios/ (The Story Files): A directory of JSON files, each defining a complete narrative with a timeline, initial conditions, and timed events (e.g., supply shocks, carbon taxes). This allows for running different experiments without changing any Python code.
8. reporting.py (The Analyst): Contains all logic for generating the final, data-intensive comparative report. It builds markdown tables and uses a specialized LLM prompt to create a narrative analysis grounded in the quantitative results.
