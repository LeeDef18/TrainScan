from typing import Protocol


class OrientationRulesRepository(Protocol):
    def get_rules_for_wagon(self, wagon_type: str) -> list[str]:
        """Return allowed orientation classes for wagon type."""
