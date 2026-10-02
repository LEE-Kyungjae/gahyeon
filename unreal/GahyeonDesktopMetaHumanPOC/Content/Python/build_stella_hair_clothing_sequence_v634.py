"""Build v634 from the proven template using Stella's v633 hair+clothing rig."""

from pathlib import Path


SOURCE = Path(__file__).with_name("build_stella_dynamics_sequence_v622.py")
code = SOURCE.read_text(encoding="utf-8")
code = code.replace("v622", "v634")
code = code.replace(
    "/Game/LivingCharacterPOC/v620/ControlRig/CR_Stella_HairDynamics_v620",
    "/Game/LivingCharacterPOC/v633/ControlRig/CR_Stella_HairClothingDynamics_v633",
)
exec(compile(code, str(SOURCE), "exec"))
