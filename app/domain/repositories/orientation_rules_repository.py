from typing import Protocol


class OrientationRulesRepository(Protocol):
    def has_wagon(self, wagon_type: str) -> bool:
        """Return whether wagon type exists in rule table."""

    def get_rules_for_wagon(self, wagon_type: str) -> list[str]:
        """Return allowed orientation classes for wagon type."""

    def get_rules_for_wagon_side(self, wagon_type: str, side: str) -> list[str]:
        """Return allowed orientation classes for wagon type and camera side."""
