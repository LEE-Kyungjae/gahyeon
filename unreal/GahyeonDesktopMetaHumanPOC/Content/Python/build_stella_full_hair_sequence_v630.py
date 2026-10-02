"""Build v630 from the proven sequence template using Stella's full-hair v629 rig."""

from pathlib import Path


SOURCE = Path(__file__).with_name("build_stella_dynamics_sequence_v622.py")
code = SOURCE.read_text(encoding="utf-8")
code = code.replace("v622", "v630")
code = code.replace(
    "/Game/LivingCharacterPOC/v620/ControlRig/CR_Stella_HairDynamics_v620",
    "/Game/LivingCharacterPOC/v629/ControlRig/CR_Stella_FullHairDynamics_v629",
)
exec(compile(code, str(SOURCE), "exec"))
