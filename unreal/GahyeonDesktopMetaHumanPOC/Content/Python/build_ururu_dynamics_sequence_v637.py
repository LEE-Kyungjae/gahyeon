"""Build Ururu's corrected living-idle sequence with layered v636 Dynamics."""

from pathlib import Path


SOURCE = Path(__file__).with_name("build_stella_dynamics_sequence_v622.py")
code = SOURCE.read_text(encoding="utf-8")
code = code.replace("v622", "v637")
code = code.replace(
    "/Game/LivingCharacterPOC/v572/Characters/StellaCentimeterNormalized/StellaLily_CentimeterNormalized_v571",
    "/Game/LivingCharacterPOC/v585/Characters/UruruCentimeterNormalized/Ururu_CentimeterNormalized_v584",
)
code = code.replace(
    "/Game/LivingCharacterPOC/v606/Animation/stella/AS_Stella_LivingIdle_v606",
    "/Game/LivingCharacterPOC/v606/Animation/ururu/AS_Ururu_LivingIdle_Corrected_v606",
)
code = code.replace(
    "/Game/LivingCharacterPOC/v620/ControlRig/CR_Stella_HairDynamics_v620",
    "/Game/LivingCharacterPOC/v636/ControlRig/CR_Ururu_HairClothingDynamics_v636",
)
code = code.replace("StellaDynamics", "UruruDynamics")
code = code.replace("Stella_Dynamics", "Ururu_Dynamics")
code = code.replace("stella-dynamics", "ururu-dynamics")
code = code.replace("Stella dynamics", "Ururu dynamics")
code = code.replace("Stella animation", "Ururu animation")
code = code.replace("Stella hair", "Ururu hair and ribbons")
code = code.replace("build_stella_dynamics_sequence_v637", "build_ururu_dynamics_sequence_v637")
exec(compile(code, str(SOURCE), "exec"))
