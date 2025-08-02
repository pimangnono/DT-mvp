class SupplyChainModel:
    def __init__(self, model_type, material_mix):
        """
        Initializes the supply chain model for an agent.
        
        Args:
            model_type (str): 'linear' or 'circular'.
            material_mix (dict): The percentage of each material used.
        """
        self.model_type = model_type
        self.material_mix = material_mix

    def calculate_cogs_modifier(self, material_prices):
        """
        Calculates the agent's cost of goods sold (COGS) based on current material prices
        and returns it as a direct modifier for the agent's profit margin.
        A higher value means higher costs and therefore a more negative impact on profit.
        """
        cogs_modifier = 0
        base_price = 100 # Assume a baseline operational cost for a stable market
        
        for material, mix_percentage in self.material_mix.items():
            cogs_modifier += (material_prices.get(material, base_price) * mix_percentage)
            
        # Return the deviation from the baseline price.
        # If new costs are 150, the modifier will be -(150-100) = -50.
        return -(cogs_modifier - base_price)