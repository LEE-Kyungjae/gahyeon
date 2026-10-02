#!/usr/bin/env python3
"""Normalize heterogeneous donor facial channels into a reusable semantic layer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


ARKIT = {
    "browdownleft": "browDownLeft", "browdownright": "browDownRight",
    "browinnerup": "browInnerUp", "browouterupleft": "browOuterUpLeft",
    "browouterupright": "browOuterUpRight", "cheekpuff": "cheekPuff",
    "cheeksquintleft": "cheekSquintLeft", "cheeksquintright": "cheekSquintRight",
    "eyeblinkleft": "eyeBlinkLeft", "eyeblinkright": "eyeBlinkRight",
    "eyesquintleft": "eyeSquintLeft", "eyesquintright": "eyeSquintRight",
    "eyewideleft": "eyeWideLeft", "eyewideright": "eyeWideRight",
    "jawforward": "jawForward", "jawleft": "jawLeft", "jawopen": "jawOpen",
    "jawright": "jawRight", "mouthclose": "mouthClose", "mouthfunnel": "mouthFunnel",
    "mouthpucker": "mouthPucker", "mouthleft": "mouthLeft", "mouthright": "mouthRight",
    "mouthsmileleft": "mouthSmileLeft", "mouthsmileright": "mouthSmileRight",
    "mouthfrownleft": "mouthFrownLeft", "mouthfrownright": "mouthFrownRight",
    "mouthdimpleleft": "mouthDimpleLeft", "mouthdimpleright": "mouthDimpleRight",
    "mouthstretchleft": "mouthStretchLeft", "mouthstretchright": "mouthStretchRight",
    "mouthrolllower": "mouthRollLower", "mouthrollupper": "mouthRollUpper",
    "mouthshruglower": "mouthShrugLower", "mouthshrugupper": "mouthShrugUpper",
    "mouthpressleft": "mouthPressLeft", "mouthpressright": "mouthPressRight",
    "mouthlowerdownleft": "mouthLowerDownLeft", "mouthlowerdownright": "mouthLowerDownRight",
    "mouthupperupleft": "mouthUpperUpLeft", "mouthupperupright": "mouthUpperUpRight",
    "nosesneerleft": "noseSneerLeft", "nosesneerright": "noseSneerRight",
}

ALIASES = {
    "mouthopen": ("jawOpen",), "mouthsmile": ("mouthSmileLeft", "mouthSmileRight"),
    "eyesclosed": ("eyeBlinkLeft", "eyeBlinkRight"),
    "eyeslookup": ("eyeLookUpLeft", "eyeLookUpRight"),
    "eyeslookdown": ("eyeLookDownLeft", "eyeLookDownRight"),
    "eyeblinkl": ("eyeBlinkLeft",), "eyeblinkr": ("eyeBlinkRight",),
    "eyesquintl": ("eyeSquintLeft",), "eyesquintr": ("eyeSquintRight",),
    "eyewidel": ("eyeWideLeft",), "eyewider": ("eyeWideRight",),
    "browdropl": ("browDownLeft",), "browdropr": ("browDownRight",),
    "browraiseinnerl": ("browInnerUp",), "browraiseinnerr": ("browInnerUp",),
    "browraiseouterl": ("browOuterUpLeft",), "browraiseouterr": ("browOuterUpRight",),
    "nosesneerl": ("noseSneerLeft",), "nosesneerr": ("noseSneerRight",),
    "cheekraisel": ("cheekSquintLeft",), "cheekraiser": ("cheekSquintRight",),
    "cheekpuffl": ("cheekPuff",), "cheekpuffr": ("cheekPuff",),
    "mouthsmilel": ("mouthSmileLeft",), "mouthsmiler": ("mouthSmileRight",),
    "mouthdimplel": ("mouthDimpleLeft",), "mouthdimpler": ("mouthDimpleRight",),
    "mouthpressl": ("mouthPressLeft",), "mouthpressr": ("mouthPressRight",),
    "mouthl": ("mouthLeft",), "mouthr": ("mouthRight",),
    "mouthclose": ("mouthClose",), "jawdown": ("jawOpen",),
}

HAYLEY_TARGETS = {
    "jawOpen": {"bones": ["cJaw"], "driver": "rotation", "calibrationRequired": True},
    "eyeBlinkLeft": {"bones": ["lEyelidUpperA", "lEyelidUpperB", "lEyelidLowerA", "lEyelidLowerB"], "driver": "paired-rotation", "calibrationRequired": True},
    "eyeBlinkRight": {"bones": ["rEyelidUpperA", "rEyelidUpperB", "rEyelidLowerA", "rEyelidLowerB"], "driver": "paired-rotation", "calibrationRequired": True},
    "eyeLook": {"bones": ["lEye", "rEye"], "driver": "rotation", "calibrationRequired": True},
    "mouthSmileLeft": {"bones": ["lLipCorner", "lCheekInner"], "driver": "translation", "calibrationRequired": True},
    "mouthSmileRight": {"bones": ["rLipCorner", "rCheekInner"], "driver": "translation", "calibrationRequired": True},
    "mouthPucker": {"bones": ["lLipCorner", "rLipCorner", "cLipUpper", "cLipLower"], "driver": "translation", "calibrationRequired": True},
    "browInnerUp": {"bones": ["lForeheadIn", "rForeheadIn", "cForehead"], "driver": "translation", "calibrationRequired": True},
    "browDownLeft": {"bones": ["lForeheadIn", "lForeheadMid"], "driver": "translation", "calibrationRequired": True},
    "browDownRight": {"bones": ["rForeheadIn", "rForeheadMid"], "driver": "translation", "calibrationRequired": True}
}


def normalized(name):
    name = re.sub(r"\s*-\s*POSITION\s*$", "", name, flags=re.IGNORECASE)
    return re.sub(r"[^a-z0-9]", "", name.lower())


def canonicalize_expression_name(name):
    value = normalized(name)
    if value in ARKIT:
        return (ARKIT[value],), "direct-standard"
    if value in ALIASES:
        return ALIASES[value], "semantic-alias"
    if value.startswith("viseme"):
        return ("viseme." + value.removeprefix("viseme"),), "viseme"
    if value.startswith("v") and value in {
        "vopen", "vexplosive", "vdentallip", "vtighto", "vtight",
        "vwide", "vaffricate", "vlipopen",
    }:
        return ("viseme." + value[1:],), "viseme"
    if value.startswith(("el", "eb", "td", "tds")) or any(
        term in value for term in ("happy", "sad", "angry", "thinking", "tired", "smile")
    ):
        return ("preset." + value,), "expression-preset"
    return (), "unmapped"


def choose_primary_mesh(report):
    preferred = [mesh for mesh in report["shapeMeshes"] if mesh["object"] in {
        "CC_Base_Body", "Narration_Donor_Body", "player_004_lacrimosa_skin_LOD1"
    }]
    if preferred:
        return preferred[0]
    return max(report["shapeMeshes"], key=lambda item: item["shapeKeyCount"])


def build_expression_channel_manifest(reports):
    donors = {}
    canonical_channels = set()
    for report in reports:
        mesh = choose_primary_mesh(report)
        mappings = []
        for key in mesh["shapeKeys"]:
            channels, method = canonicalize_expression_name(key["source"])
            canonical_channels.update(channels)
            mappings.append({
                "source": key["source"],
                "channels": list(channels),
                "method": method,
            })
        mapped = sum(1 for item in mappings if item["channels"])
        donors[report["id"]] = {
            "source": report["source"],
            "mesh": mesh["object"],
            "sourceChannelCount": len(mappings),
            "mappedChannelCount": mapped,
            "coverage": round(mapped / max(len(mappings), 1), 4),
            "mappings": mappings,
        }
    return {
        "schemaVersion": 1,
        "iteration": "v386",
        "status": "draft-semantic-expression-channel-manifest",
        "canonicalChannels": sorted(canonical_channels),
        "donors": donors,
        "target": {
            "id": "hayley",
            "mechanism": "facial-bone-drivers",
            "channelTargets": HAYLEY_TARGETS,
            "calibrationStatus": "required-before-animation-transfer",
        },
        "policy": {
            "copyShapeKeysAcrossTopology": False,
            "preserveSourceCurves": True,
            "automaticApproval": False,
            "releaseEligible": False,
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite manifest: {args.output}")
    reports = [json.loads(path.read_text()) for path in args.input]
    manifest = build_expression_channel_manifest(reports)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({
        "canonicalChannelCount": len(manifest["canonicalChannels"]),
        "donors": {
            key: {
                "sourceChannelCount": value["sourceChannelCount"],
                "mappedChannelCount": value["mappedChannelCount"],
                "coverage": value["coverage"],
            }
            for key, value in manifest["donors"].items()
        },
    }))


if __name__ == "__main__":
    main()
