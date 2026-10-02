"""Render the verified v413 compound jawOpen asset at its measured UE scale."""

from pathlib import Path


def capture_hayley_compound_jawopen_sheet_v414():
    source_path = Path(__file__).with_name("build_hayley_jawopen_contact_sheet_v407.py")
    source = source_path.read_text()
    source = source.replace("v407", "v414").replace("V407", "V414")
    source = source.replace(
        "/Game/LivingCharacterPOC/v406/JawOpenImport/Hayley_JawOpen_v405",
        "/Game/LivingCharacterPOC/v413/CompoundJawOpenImport/Hayley_CompoundJawOpen_v411",
    )
    source = source.replace(
        "/Game/LivingCharacterPOC/v406/JawOpenImport/Hayley_JawOpen_v405_Anim",
        "/Game/LivingCharacterPOC/v413/CompoundJawOpenImport/Hayley_CompoundJawOpen_v411_Anim",
    )
    source = source.replace(
        'actor.set_actor_scale3d(unreal.Vector(0.1, 0.1, 0.1))',
        'actor.set_actor_scale3d(unreal.Vector(1.0, 1.0, 1.0))',
    )
    source = source.replace("jaw-open-18deg", "compound-jaw-open")
    exec(compile(source, str(source_path), "exec"), {"__name__": "__main__"})


capture_hayley_compound_jawopen_sheet_v414()
