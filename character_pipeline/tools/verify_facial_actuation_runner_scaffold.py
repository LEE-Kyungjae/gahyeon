#!/usr/bin/env python3
"""Static fail-closed verification for the UE 5.6 P36 execution path."""
import argparse,json
from pathlib import Path
def verify(root):
 root=Path(root);header=(root/"unreal/GahyeonStage/Source/GahyeonStage/Public/Presentation/GahyeonCharacterPresentationProfile.h").read_text();source=(root/"unreal/GahyeonStage/Source/GahyeonStage/Private/Presentation/GahyeonCharacterPresentationProfile.cpp").read_text();component=(root/"unreal/GahyeonStage/Source/GahyeonStage/Private/Presentation/GahyeonCharacterPresentationComponent.cpp").read_text();bridge=(root/"unreal/GahyeonStage/Source/GahyeonStage/Public/Presentation/GahyeonFacialControlRigBridge.h").read_text();anim_header=(root/"unreal/GahyeonStage/Source/GahyeonStage/Public/Animation/GahyeonCharacterAnimInstance.h").read_text();anim_source=(root/"unreal/GahyeonStage/Source/GahyeonStage/Private/Animation/GahyeonCharacterAnimInstance.cpp").read_text();test=(root/"unreal/GahyeonStage/Source/GahyeonStage/Private/Tests/GahyeonFacialCurveBindingTest.cpp").read_text();runner=(root/"unreal/GahyeonStage/Content/Python/gahyeon_run_facial_actuation_capture.py").read_text();preflight=(root/"unreal/GahyeonStage/Content/Python/gahyeon_prepare_facial_actuation_capture.py").read_text()
 for token in ('UFUNCTION(BlueprintCallable, Category = "Gahyeon|Presentation|QA")','ResolveFacialSemanticWeights'):
  if token not in header:raise ValueError(f"facial semantic API missing token: {token}")
 for token in ('Group == TEXT("direct")','TEXT("blink-left")','TEXT("blink-right")','TEXT("jaw-open")','AddBoundWeight(VisemeCurves','AddBoundWeight(EmotionCurves'):
  if token not in source:raise ValueError(f"facial semantic resolver missing token: {token}")
 for token in ('left blink never leaks to right blink','right blink never leaks to left blink','unknown explicit semantic fails closed'):
  if token not in test:raise ValueError(f"facial semantic automation test missing: {token}")
 for token in ('ApplyFacialControlRigCurves','GetFacialControlRigCurveWeights','BlueprintNativeEvent'):
  if token not in bridge:raise ValueError(f"Control Rig bridge contract missing: {token}")
 for token in ('ImplementsInterface','Execute_ApplyFacialControlRigCurves','AppliedControlRigCurves'):
  if token not in component:raise ValueError(f"presentation component route missing: {token}")
 for token in ('public IGahyeonFacialControlRigBridge','GetFacialControlRigCurves','ConfirmFacialControlRigConsumed','GetConsumedFacialControlRigToken','GetConsumedFacialControlRigDigest','GahyeonFacialControlRigCurves'):
  if token not in anim_header:raise ValueError(f"native AnimInstance bridge missing: {token}")
 for token in ('ApplyFacialControlRigCurves_Implementation','GetFacialControlRigCurveWeights_Implementation','ConfirmFacialControlRigConsumed','FacialCurveDigest','ConsumedFacialControlRigCurves','Item.Value > 1.0f','GahyeonFacialControlRigCurves.Remove'):
  if token not in anim_source:raise ValueError(f"native AnimInstance bridge behavior missing: {token}")
 for token in ('resolve_facial_semantic_weights','get_morph_target','set_morph_target','take_high_res_screenshot(1440,2560','register_slate_post_tick_callback','expected exactly one actor','GahyeonFacialControlRigBridge','apply_facial_control_rig_curves','get_pending_facial_control_rig_token','get_consumed_facial_control_rig_token','get_consumed_facial_control_rig_digest','Control Rig graph did not acknowledge','get_facial_control_rig_curve_weights','len(self.queue)!=57','refusing to use existing immutable actuation output root','failure.json'):
  if token not in runner:raise ValueError(f"P36 runner missing fail-closed token: {token}")
 for token in ('exactSampleCount','moviePipelinePresetExists','nativeFaceAnimBridgeAvailable','faceAnimBlueprintInheritsNativeBridge','neverOverwrite','failed closed'):
  if token not in preflight:raise ValueError(f"P36 preflight missing token: {token}")
 return {"valid":True,"explicitSemanticResolver":True,"asymmetricBlink":True,"samples":57,"resolution":[1440,2560],"controlRigExecution":"typed-bridge-required"}
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",type=Path,default=Path.cwd());a=p.parse_args();print(json.dumps(verify(a.root.resolve())));return 0
if __name__=="__main__":raise SystemExit(main())
