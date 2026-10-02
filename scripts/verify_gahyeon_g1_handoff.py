#!/usr/bin/env python3
"""Verify a packaged G1 handoff without extracting it."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
IDENTITY_SCHEMA = ROOT / "docs/contracts/gahyeon-identity-reference.schema.json"
MODELING_SCHEMA = ROOT / "docs/contracts/gahyeon-modeling-input.schema.json"
G1_REVIEW_SCHEMA = ROOT / "docs/contracts/gahyeon-g1-review.schema.json"


def verify_archive(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or "package-manifest.json" not in names:
            raise ValueError("archive has duplicate entries or no package manifest")
        inventory = json.loads(archive.read("package-manifest.json"))
        expected = {item["path"]: item for item in inventory["files"]}
        actual = set(names) - {"package-manifest.json"}
        if actual != set(expected):
            raise ValueError("archive contents do not match package manifest")
        for name, item in expected.items():
            data = archive.read(name)
            if len(data) != item["bytes"]:
                raise ValueError(f"size mismatch: {name}")
            if hashlib.sha256(data).hexdigest() != item["sha256"]:
                raise ValueError(f"checksum mismatch: {name}")
        identity = json.loads(archive.read("identity-reference.json"))
        modeling = json.loads(archive.read("modeling-input.json"))
        review = json.loads(archive.read("g1-review-template.json"))
        work_order = json.loads(archive.read("g1-authoring-work-order.json"))
        drafts = json.loads(archive.read("g1-drafts/drafts-manifest.json"))
        jsonschema.Draft202012Validator(
            json.loads(IDENTITY_SCHEMA.read_text(encoding="utf-8"))).validate(identity)
        jsonschema.Draft202012Validator(
            json.loads(MODELING_SCHEMA.read_text(encoding="utf-8"))).validate(modeling)
        jsonschema.Draft202012Validator(
            json.loads(G1_REVIEW_SCHEMA.read_text(encoding="utf-8"))).validate(review)
        if modeling.get("identityManifest") != "identity-reference.json":
            raise ValueError("modeling input does not bind the packaged identity manifest")
        canonical = {item["file"] for item in identity["references"]}
        supporting = {item["file"] for item in identity["supportingReferences"]}
        if canonical & supporting:
            raise ValueError("canonical and supporting evidence overlap")
        reference_entries = inventory.get("references", [])
        if inventory.get("schemaVersion") != 2:
            raise ValueError("unsupported G1 handoff manifest version")
        if inventory.get("referencePathPolicy") != "portable-ascii-alias-v1":
            raise ValueError("portable reference path policy is missing")
        if len(reference_entries) != len(canonical | supporting):
            raise ValueError("reference alias count mismatch")
        reference_by_index = {}
        classified = set()
        for item in reference_entries:
            index = item.get("index")
            packaged_path = item.get("packagedPath", "")
            classification = item.get("classification")
            if index in reference_by_index:
                raise ValueError(f"duplicate packaged reference index: {index}")
            if not re.fullmatch(r"references/(canonical|supporting)/ref-[0-9]{3}\.[a-z0-9]+",
                                packaged_path):
                raise ValueError(f"non-portable packaged reference path: {packaged_path}")
            if not packaged_path.isascii() or packaged_path.split("/")[1] != classification:
                raise ValueError(f"reference path classification mismatch: {packaged_path}")
            if packaged_path not in expected:
                raise ValueError(f"packaged reference is missing: {packaged_path}")
            archived = expected[packaged_path]
            if item.get("bytes") != archived.get("bytes") or item.get("sha256") != archived.get("sha256"):
                raise ValueError(f"reference inventory mismatch: {packaged_path}")
            reference_by_index[index] = item
            classified.add(packaged_path)
        identity_by_index = {
            item["index"]: ("canonical", item) for item in identity["references"]
        } | {
            item["index"]: ("supporting", item) for item in identity["supportingReferences"]
        }
        if set(reference_by_index) != set(identity_by_index):
            raise ValueError("reference aliases do not cover the identity manifest")
        for index, (classification, source) in identity_by_index.items():
            packaged = reference_by_index[index]
            if packaged.get("classification") != classification:
                raise ValueError(f"reference classification changed: {index}")
            if packaged.get("sourceFile") != source["file"]:
                raise ValueError(f"reference source filename changed: {index}")
            if packaged.get("sha256") != source["sha256"]:
                raise ValueError(f"reference source checksum changed: {index}")
        if inventory.get("referenceMap") != "reference-map.csv":
            raise ValueError("reference map is not declared")
        if inventory.get("usageGuide") != "README.md":
            raise ValueError("usage guide is not declared")
        reference_map_data = archive.read("reference-map.csv")
        if not reference_map_data.startswith(b"\xef\xbb\xbf"):
            raise ValueError("reference map must use UTF-8 BOM for spreadsheet compatibility")
        map_rows = list(csv.DictReader(io.StringIO(reference_map_data.decode("utf-8-sig"))))
        expected_rows = [
            {key: str(item[key]) for key in
             ("index", "classification", "packagedPath", "sourceFile", "bytes", "sha256")}
            for item in reference_entries
        ]
        if map_rows != expected_rows:
            raise ValueError("reference map does not match package references")
        guide = archive.read("README.md").decode("utf-8")
        if ("non-authoritative generated drafts" not in guide
                or "reference-map.csv" not in guide
                or "tools/build-g1-scene-plan.py" not in guide
                or "tools/blender-bootstrap-g1.py" not in guide
                or "tools/blender-import-g1-base.py" not in guide
                or "tools/blender-render-g1-evidence.py" not in guide
                or "tools/package-g1-submission.py" not in guide):
            raise ValueError("usage guide omits authority or reference mapping guidance")
        workstation_tools = {
            "tools/build-g1-scene-plan.py",
            "tools/blender-bootstrap-g1.py",
            "tools/blender-import-g1-base.py",
            "tools/blender-render-g1-evidence.py",
            "tools/package-g1-submission.py",
        }
        if set(inventory.get("workstationTools", [])) != workstation_tools:
            raise ValueError("standalone G1 workstation tools are not declared")
        metadata = {"identity-reference.json", "modeling-input.json", "g1-review-template.json",
                    "g1-authoring-work-order.json", "g1-drafts/drafts-manifest.json",
                    "reference-map.csv", "README.md"} | workstation_tools
        draft_files = {f"g1-drafts/{item['file']}" for item in drafts.get("assets", [])}
        if classified | metadata | draft_files != actual:
            raise ValueError("archive includes unclassified image candidates")
        if inventory.get("referenceCount") != len(classified):
            raise ValueError("reference count mismatch")
        if inventory.get("canonicalReferenceCount") != len(canonical):
            raise ValueError("canonical reference count mismatch")
        if inventory.get("supportingReferenceCount") != len(supporting):
            raise ValueError("supporting reference count mismatch")
        if inventory.get("sourceInventory") != identity.get("sourceInventory"):
            raise ValueError("source inventory discrepancy was not preserved")
        if inventory.get("reviewTemplate") != "g1-review-template.json":
            raise ValueError("G1 review template is not declared")
        if inventory.get("authoringWorkOrder") != "g1-authoring-work-order.json":
            raise ValueError("G1 authoring work order is not declared")
        if drafts.get("status") != "draft" or drafts.get("identityAuthority") is not False:
            raise ValueError("Packaged generated drafts must remain non-authoritative")
        if inventory.get("nonAuthoritativeDraftCount") != len(draft_files):
            raise ValueError("non-authoritative draft count mismatch")
        if inventory.get("nonAuthoritativeDraftManifest") != "g1-drafts/drafts-manifest.json":
            raise ValueError("non-authoritative draft manifest is not declared")
        for item in drafts.get("assets", []):
            data = archive.read(f"g1-drafts/{item['file']}")
            if hashlib.sha256(data).hexdigest() != item.get("sha256"):
                raise ValueError(f"draft manifest checksum mismatch: {item.get('file')}")
        work_sources = {item["role"]: item for item in work_order.get("sourceManifests", [])}
        expected_work_sources = {
            "identity": "identity-reference.json",
            "modeling-input": "modeling-input.json",
            "non-authoritative-drafts": "g1-drafts/drafts-manifest.json",
        }
        if set(work_sources) != set(expected_work_sources):
            raise ValueError("G1 work order source bindings are incomplete")
        for role, source_name in expected_work_sources.items():
            item = work_sources[role]
            if item.get("uri") != source_name:
                raise ValueError(f"G1 work order source URI mismatch: {role}")
            if item.get("sha256") != hashlib.sha256(archive.read(source_name)).hexdigest():
                raise ValueError(f"G1 work order source checksum mismatch: {role}")
        if review.get("status") != "draft" or review.get("evidence") or review.get("approvals"):
            raise ValueError("Packaged G1 review template must remain an unapproved empty draft")
        review_sources = {item["kind"]: item for item in review.get("sourceManifests", [])}
        expected_sources = {
            "identity-reference": hashlib.sha256(archive.read("identity-reference.json")).hexdigest(),
            "modeling-input": hashlib.sha256(archive.read("modeling-input.json")).hexdigest(),
        }
        if set(review_sources) != set(expected_sources):
            raise ValueError("G1 review template has invalid source manifest bindings")
        for kind, expected_sha in expected_sources.items():
            item = review_sources[kind]
            if item.get("sha256") != expected_sha:
                raise ValueError(f"G1 review template source checksum mismatch: {kind}")
        canonical_indices = {item["index"] for item in identity["references"]}
        supporting_indices = {item["index"] for item in identity["supportingReferences"]}
        if canonical_indices & supporting_indices:
            raise ValueError("canonical and supporting indices overlap")
        modeling_indices = {
            index for values in modeling["anchors"].values() for index in values
        }
        authority = modeling["geometryAuthority"]
        modeling_indices.add(authority["masterNeutralFace"])
        for key, values in authority.items():
            if key != "masterNeutralFace":
                modeling_indices.update(values)
        if not modeling_indices.issubset(canonical_indices):
            raise ValueError("supporting evidence was promoted into modeling geometry authority")
        return inventory


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    result = verify_archive(args.archive)
    print(
        f"G1 handoff OK: {result['canonicalReferenceCount']} canonical + "
        f"{result['supportingReferenceCount']} supporting references")


if __name__ == "__main__":
    main()
