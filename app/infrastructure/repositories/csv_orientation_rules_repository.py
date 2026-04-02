import csv

from app.domain.repositories.orientation_rules_repository import (
    OrientationRulesRepository,
)


class CsvOrientationRulesRepository(OrientationRulesRepository):
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._rules = self._load_rules()

    def _load_rules(self) -> dict[str, list[str]]:
        rules: dict[str, list[str]] = {}

        with open(self.file_path, encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                wagon_type = (row.get("Model") or "").strip()
                objects = (row.get("Objects") or "").split(",")
                rules[wagon_type] = [item.strip() for item in objects if item.strip()]

        return rules

    def get_rules_for_wagon(self, wagon_type: str) -> list[str]:
        return self._rules.get(wagon_type, [])
