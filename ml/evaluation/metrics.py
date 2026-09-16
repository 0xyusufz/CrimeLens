"""Entity/relationship precision, recall, and F1 evaluation utilities.

This module intentionally reports measurements instead of declaring a generic
"accuracy" number.  Graph extraction has multiple labels and a precision-first
policy, so entity and relationship F1 are the meaningful measures.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Callable, Iterable


@dataclass(frozen=True)
class MetricScore:
    true_positive: int
    false_positive: int
    false_negative: int
    precision: float
    recall: float
    f1: float


@dataclass(frozen=True)
class EvaluationReport:
    entity: MetricScore
    relationship: MetricScore
    cases: int

    @property
    def macro_f1(self) -> float:
        return round((self.entity.f1 + self.relationship.f1) / 2.0, 4)

    def as_dict(self) -> dict[str, Any]:
        return {
            "cases": self.cases,
            "entity": self.entity.__dict__,
            "relationship": self.relationship.__dict__,
            "macro_f1": self.macro_f1,
        }


def _normal(value: str) -> str:
    return " ".join(str(value).casefold().split())


def _metric(predicted: set[tuple[str, ...]], expected: set[tuple[str, ...]]) -> MetricScore:
    tp = len(predicted & expected)
    fp = len(predicted - expected)
    fn = len(expected - predicted)
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
    return MetricScore(tp, fp, fn, round(precision, 4), round(recall, 4), round(f1, 4))


def _entity_set(items: Iterable[Any]) -> set[tuple[str, str]]:
    output: set[tuple[str, str]] = set()
    for item in items:
        if hasattr(item, "type") and hasattr(item, "name"):
            entity_type = item.type.value if hasattr(item.type, "value") else str(item.type)
            name = item.name
        elif isinstance(item, dict):
            entity_type = item.get("type", "")
            name = item.get("name", "")
        else:
            continue
        output.add((str(entity_type).upper(), _normal(str(name))))
    return output


def _relationship_set(items: Iterable[Any], entities: Iterable[Any]) -> set[tuple[str, str, str]]:
    names_by_id: dict[str, str] = {}
    for entity in entities:
        if hasattr(entity, "id") and hasattr(entity, "name"):
            names_by_id[str(entity.id)] = _normal(str(entity.name))
        elif isinstance(entity, dict):
            names_by_id[str(entity.get("id") or "")] = _normal(str(entity.get("name") or ""))
    output: set[tuple[str, str, str]] = set()
    for item in items:
        if hasattr(item, "relationship"):
            relation = item.relationship.value if hasattr(item.relationship, "value") else str(item.relationship)
            source = names_by_id.get(item.source_entity_id, _normal(item.source_entity_id))
            target = names_by_id.get(item.target_entity_id, _normal(item.target_entity_id))
        elif isinstance(item, dict):
            relation = item.get("relationship") or item.get("type") or ""
            source = _normal(item.get("source") or item.get("source_name") or "")
            target = _normal(item.get("target") or item.get("target_name") or "")
        else:
            continue
        output.add((_normal(source), str(relation).upper(), _normal(target)))
    return output


def score_prediction(prediction: Any, expected: dict[str, Any]) -> tuple[MetricScore, MetricScore]:
    entities = prediction.get("entities", []) if isinstance(prediction, dict) else prediction.entities
    relationships = prediction.get("relationships", []) if isinstance(prediction, dict) else prediction.relationships
    predicted_entities = _entity_set(entities)
    expected_entities = _entity_set(expected.get("entities", []))
    predicted_relationships = _relationship_set(relationships, entities)
    expected_relationships = {
        (_normal(item["source"]), str(item["relationship"]).upper(), _normal(item["target"]))
        for item in expected.get("relationships", [])
    }
    return _metric(predicted_entities, expected_entities), _metric(predicted_relationships, expected_relationships)


def evaluate_benchmark(
    benchmark_path: str | Path,
    processor: Callable[..., Any],
) -> EvaluationReport:
    """Run a labeled JSON benchmark through a processor and aggregate micro scores."""
    payload = json.loads(Path(benchmark_path).read_text(encoding="utf-8"))
    cases = list(payload.get("cases") or [])
    entity_predicted: set[tuple[str, ...]] = set()
    entity_expected: set[tuple[str, ...]] = set()
    relationship_predicted: set[tuple[str, ...]] = set()
    relationship_expected: set[tuple[str, ...]] = set()
    for case in cases:
        result = processor(document_id=str(case["id"]), text=str(case["text"]))
        entities = result.entities if hasattr(result, "entities") else result["entities"]
        relationships = result.relationships if hasattr(result, "relationships") else result["relationships"]
        prefix = str(case["id"])
        entity_predicted |= {(prefix, *item) for item in _entity_set(entities)}
        entity_expected |= {(prefix, *item) for item in _entity_set(case.get("expected", {}).get("entities", []))}
        relationship_predicted |= {(prefix, *item) for item in _relationship_set(relationships, entities)}
        relationship_expected |= {
            (prefix, _normal(item["source"]), str(item["relationship"]).upper(), _normal(item["target"]))
            for item in case.get("expected", {}).get("relationships", [])
        }
    return EvaluationReport(
        entity=_metric(entity_predicted, entity_expected),
        relationship=_metric(relationship_predicted, relationship_expected),
        cases=len(cases),
    )


__all__ = ["EvaluationReport", "MetricScore", "evaluate_benchmark", "score_prediction"]
