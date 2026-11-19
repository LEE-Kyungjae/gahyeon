"""Add the proven Gahyeon Stage voice runtime to Diana's immutable macOS v418 map."""

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE_MAP = "/Game/Gahyeon/Character2/Diana/v418/Runtime/L_DianaMacRuntimeShoulderOccluded_v418"
OUTPUT_MAP = "/Game/Gahyeon/Character2/Diana/v419/Runtime/L_DianaMacRuntimeVoice_v419"
REPORT = ROOT / "artifacts/gahyeon-ch/iterations/v419-diana-macos-voice-runtime/report.json"

if REPORT.exists() or unreal.EditorAssetLibrary.does_asset_exist(OUTPUT_MAP):
    raise RuntimeError("refusing to overwrite immutable Diana v419 outputs")
unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if world is None:
    raise RuntimeError("v418 world unavailable")

voice_pawn = actors.spawn_actor_from_class(
    unreal.GahyeonCharacterPawn,
    unreal.Vector(2000.0, 2000.0, -2000.0),
    unreal.Rotator(),
)
if voice_pawn is None:
    raise RuntimeError("failed to spawn Gahyeon voice pawn")
voice_pawn.set_actor_label("Diana_MacVoiceRuntime_v419")
voice_pawn.set_actor_hidden_in_game(True)
voice = voice_pawn.get_component_by_class(unreal.GahyeonVoiceInputComponent)
if voice is None:
    raise RuntimeError("voice input component unavailable")

if not unreal.EditorLoadingAndSavingUtils.save_map(world, OUTPUT_MAP):
    raise RuntimeError("failed to save Diana v419 voice runtime")
report = {
    "schemaVersion": 1,
    "iteration": "v419-diana-macos-voice-runtime",
    "status": "candidate",
    "sourceMap": SOURCE_MAP,
    "map": OUTPUT_MAP,
    "voiceRuntime": "shared GahyeonStage/GahyeonRuntimeCore modules",
    "captureStartArgument": "-GahyeonAutoStartMicrophone",
    "sttMode": "batch WAV fallback",
    "ttsPlayback": "GahyeonSpeechAudioComponent via auto-created presentation host",
    "electronRetired": True,
    "humanApproved": False,
    "productionReady": False,
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.SystemLibrary.quit_editor()
