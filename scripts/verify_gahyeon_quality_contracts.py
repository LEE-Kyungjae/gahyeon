#!/usr/bin/env python3
"""Check that G1-G5 schemas and verifier semantic sets cannot drift apart."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]


def find_view_enum(value: object) -> set[str] | None:
    if isinstance(value, dict):
        properties = value.get("properties")
        if isinstance(properties, dict):
            view = properties.get("view")
            if isinstance(view, dict) and isinstance(view.get("enum"), list):
                return set(view["enum"])
        for child in value.values():
            found = find_view_enum(child)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_view_enum(child)
            if found is not None:
                return found
    return None


def approved_evidence_minimum(schema: dict) -> int | None:
    for clause in schema.get("allOf", []):
        then = clause.get("then", {})
        value = then.get("properties", {}).get("evidence", {}).get("minItems")
        if isinstance(value, int):
            return value
    return None


def verify() -> dict:
    results = []
    for gate in range(1, 6):
        schema_path = ROOT / f"docs/contracts/gahyeon-g{gate}-review.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        module = importlib.import_module(f"verify_gahyeon_g{gate}_review")
        required = set(module.REQUIRED_VIEWS)
        allowed = find_view_enum(schema)
        if allowed is None:
            raise ValueError(f"G{gate} schema has no evidence view enum")
        optional = set(getattr(module, "OPTIONAL_VIEWS", set()))
        if allowed != required | optional:
            raise ValueError(
                f"G{gate} schema/verifier evidence drift: "
                f"schemaOnly={sorted(allowed - required - optional)}, "
                f"verifierOnly={sorted(required - allowed)}")
        minimum = approved_evidence_minimum(schema)
        if minimum != len(required):
            raise ValueError(
                f"G{gate} approved evidence minimum {minimum} != required count {len(required)}")
        results.append({"gate": f"G{gate}", "requiredViews": len(required),
                        "optionalViews": len(optional)})

    hero_schema = json.loads(
        (ROOT / "docs/contracts/gahyeon-hero-asset.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(hero_schema)
    return {"valid": True, "gates": results}


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False))
