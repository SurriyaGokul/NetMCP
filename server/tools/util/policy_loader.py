import yaml
from pathlib import Path

class PolicyRegistry:
    def __init__(self, policy_root: str = "policy/config_cards"):
        self.cards = {}
        self.load_cards(policy_root)

    def load_cards(self, root: str):
        # Support both .yml and .yaml extensions
        for pattern in ["*.yml", "*.yaml"]:
            for file in Path(root).glob(pattern):
                with open(file) as f:
                    data = yaml.safe_load(f)
                    # Handle both list format (YAML files starting with -) and dict format
                    if isinstance(data, list):
                        # If it's a list, process each item
                        for card in data:
                            if isinstance(card, dict):
                                key = card.get("id")
                                if key:
                                    self.cards[key] = card
                    elif isinstance(data, dict):
                        # If it's a single dict
                        key = data.get("id")
                        if key:
                            self.cards[key] = data

    def get(self, key: str):
        return self.cards.get(key)

    def list(self):
        return list(self.cards.keys())

    def validate_value(self, key: str, value):
        card = self.cards.get(key)
        if not card:
            return f"Unknown parameter {key} not present in config cards"
        safe = card.get("safe", {}).get("constraints", {})
        if "min" in safe and value < safe["min"]:
            return f"{key} below min {safe['min']}"
        if "max" in safe and value > safe["max"]:
            return f"{key} above max {safe['max']}"
        return None
