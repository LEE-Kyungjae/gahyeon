"""Run the v622 sequence builder as immutable v624 with the layered v623 rig."""

from pathlib import Path


SOURCE = Path(__file__).with_name("build_stella_dynamics_sequence_v622.py")
code = SOURCE.read_text(encoding="utf-8")
code = code.replace("v622", "v624")
code = code.replace(
    "/Game/LivingCharacterPOC/v620/ControlRig/CR_Stella_HairDynamics_v620",
    "/Game/LivingCharacterPOC/v623/ControlRig/CR_Stella_HairDynamics_Layered_v623",
)
exec(compile(code, str(SOURCE), "exec"))
