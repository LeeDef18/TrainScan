import csv
from collections.abc import Iterable

from app.domain.repositories.orientation_rules_repository import (
    OrientationRulesRepository,
)


class CsvOrientationRulesRepository(OrientationRulesRepository):
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._rules = self._load_rules()

    def _load_rules(self) -> dict[str, dict[str, list[str]]]:
        rules: dict[str, dict[str, list[str]]] = {}

        with open(self.file_path, encoding="utf-8-sig") as csv_file:
            sample = csv_file.read(4096)
            csv_file.seek(0)
            reader = csv.DictReader(csv_file, delimiter=self._detect_delimiter(sample))
            for row in reader:
                wagon_type = self._get_model_value(row)
                if not wagon_type:
                    continue

                right_objects = row.get("objects_right")
                left_objects = row.get("objects_left")
                legacy_objects = row.get("Objects")
                rules[wagon_type] = {
                    "right": self._parse_objects(right_objects or legacy_objects),
                    "left": self._parse_objects(left_objects),
                }

        return rules

    @staticmethod
    def _get_model_value(row: dict[str, str]) -> str:
        return (row.get("Model") or row.get("Models") or "").strip()

    @staticmethod
    def _detect_delimiter(sample: str) -> str:
        header = sample.splitlines()[0] if sample else ""
        if ";" in header:
            return ";"
        return ","

    @staticmethod
    def _parse_objects(value: str | None) -> list[str]:
        if value is None:
            return []

        normalized = value.strip()
        if not normalized or normalized.lower() == "none":
            return []

        return [item.strip() for item in normalized.split(",") if item.strip()]

    @staticmethod
    def _unique_sorted(values: Iterable[str]) -> list[str]:
        return sorted(set(values))

    def get_rules_for_wagon(self, wagon_type: str) -> list[str]:
        side_rules = self._rules.get(wagon_type, {})
        return self._unique_sorted(
            [*side_rules.get("right", []), *side_rules.get("left", [])]
        )

    def get_rules_for_wagon_side(self, wagon_type: str, side: str) -> list[str]:
        return self._rules.get(wagon_type, {}).get(side, [])

    def has_wagon(self, wagon_type: str) -> bool:
        return wagon_type in self._rules
