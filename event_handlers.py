# event_handlers.py
"""
This module contains a registry of handler functions for different
types of scenario events. It decouples event logic from the core
simulation engine.
"""

# --- Event Handler Functions ---

def handle_price_change(event_effect, economy):
    """
    Handles a 'price_change' event by updating the material prices
    in the specified economy's environment.
    """
    material = event_effect.get('material')
    change = event_effect.get('change_percent', 0)
    if material in economy.environment.material_prices:
        current_price = economy.environment.material_prices[material]
        new_price = current_price * (1 + change / 100.0)
        economy.environment.material_prices[material] = new_price
        print(f">> Price Update: '{material}' price changed by {change}%. New price: {new_price:.2f}")

def handle_carbon_tax(event_effect, economy):
    """
    Handles a 'carbon_tax' event by applying the tax cost to all
    agents within the specified economy.
    """
    tax_rate = event_effect.get('tax_rate_per_ton_co2e', 0)
    if tax_rate > 0 and economy.agents:
        # The tax hits every agent in the economy
        for agent in economy.agents:
            agent.apply_carbon_tax(tax_rate, economy.lca_auditor)

# --- Event Registry ---

# This dictionary maps the 'type' string from the JSON to the handler function.
# To add a new event, you just add a new entry here.
EVENT_HANDLERS = {
    'price_change': handle_price_change,
    'carbon_tax': handle_carbon_tax,
    # 'new_event_type': handle_new_event, <-- Example of how to extend
}

def process_event(event, economy):
    """
    The main processor function. It looks up the correct handler from
    the registry and executes it for each effect in the event.
    """
    print(f"\n>> ENV_EVENT TRIGGERED: '{event['name']}' ({event['description']})")
    for effect in event.get('effects', []):
        event_type = effect.get('type')
        handler = EVENT_HANDLERS.get(event_type)
        
        if handler:
            # If a handler is found, execute it
            handler(effect, economy)
        else:
            print(f"Warning: No handler found for event type '{event_type}'. Ignoring.")