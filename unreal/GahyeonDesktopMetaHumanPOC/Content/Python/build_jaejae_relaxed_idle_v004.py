"""Replace crouch review playback with a same-skeleton standing/breathing candidate."""
import json
import math
from pathlib import Path
import unreal

ROOT = Path('/Users/ze/work/gahyeonbot')
OUT = ROOT / 'artifacts/jaejae-relaxed-idle-v004'
SOURCE = '/Game/Gahyeon/Land/Roster_v001/jaejae_v2/Source/Character_Anim'
DEST = '/Game/Gahyeon/Land/Jaejae/Idle_v004'
MAP_SOURCE = '/Game/Gahyeon/Land/Roster_v003/jaejae_v2/L_Character'
assert not unreal.EditorAssetLibrary.does_directory_exist(DEST), 'immutable iteration exists'
source = unreal.load_asset(SOURCE)
target = unreal.EditorAssetLibrary.duplicate_asset(SOURCE, DEST + '/AS_StandingBreath')
names = [str(n) for n in unreal.AnimationLibrary.get_animation_track_names(source)]
assert all(n in names for n in ['hips','spine','spine1','spine2','head','leftfoot','rightfoot'])

# Solve upper-arm directions in component space, then convert back into parent local space.
# The source first frame is an A/rest pose, not an acceptable standing idle.
parents = {'ctrl_cog':'gahyeonsceneroot','hips':'ctrl_cog','spine':'hips','spine1':'spine','spine2':'spine1',
'leftshoulder':'spine2','leftarm':'leftshoulder','leftforearm':'leftarm','lefthand':'leftforearm',
'rightshoulder':'spine2','rightarm':'rightshoulder','rightforearm':'rightarm','righthand':'rightforearm',
'leftupleg':'hips','leftleg':'leftupleg','leftfoot':'leftleg','rightupleg':'hips','rightleg':'rightupleg','rightfoot':'rightleg'}
base_pose = {n:unreal.AnimationLibrary.get_bone_pose_for_frame(source,n,0,False) for n in names}
arm_rotations = {}
def component_pose(bone):
    pose = base_pose[bone]
    q = arm_rotations.get(bone,pose.rotation)
    if bone not in parents: return pose.translation,q
    p,r = component_pose(parents[bone])
    return p+r.rotate_vector(pose.translation), r*q

def unit(v): return v/v.length()
def align(a,b):
    a,b=unit(a),unit(b)
    c=unreal.Vector(a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x)
    w=1+a.x*b.x+a.y*b.y+a.z*b.z
    length=math.sqrt(c.x*c.x+c.y*c.y+c.z*c.z+w*w)
    assert length>0.01
    return unreal.Quat(c.x/length,c.y/length,c.z/length,w/length)

hip,_=component_pose('hips')
lf,_=component_pose('leftfoot');rf,_=component_pose('rightfoot')
down=unit((lf+rf)*0.5-hip)
lp,_=component_pose('leftarm');rp,_=component_pose('rightarm')
side_axis=unit(lp-rp)
arm_metrics={}
for side,sign in [('left',1),('right',-1)]:
    bone=side+'arm'
    elbow=side+'forearm'
    pos,rotation=component_pose(bone)
    end,_=component_pose(elbow)
    _,parent_rotation=component_pose(parents[bone])
    desired=unit(down+side_axis*(sign*0.26))
    delta=align(end-pos,desired)
    inverse=unreal.Quat(-parent_rotation.x,-parent_rotation.y,-parent_rotation.z,parent_rotation.w)
    arm_rotations[bone]=inverse*delta*rotation
    new_end,_=component_pose(elbow)
    actual=unit(new_end-pos)
    angle=math.degrees(math.acos(max(-1,min(1,actual.x*down.x+actual.y*down.y+actual.z*down.z))))
    assert angle<18, (bone,angle)
    hand,_=component_pose(side+'hand')
    arm_metrics[side]={'upperArmDegreesFromDown':angle,'handPosition':str(hand),'shoulderPosition':str(pos)}

frames = int(unreal.AnimationLibrary.get_num_frames(source)) + 1
controller = target.get_editor_property('controller')
controller.open_bracket('Standing breath without crouch', False)
try:
    for bone in names:
        base = unreal.AnimationLibrary.get_bone_pose_for_frame(source, bone, 0, False)
        positions, rotations, scales = [], [], []
        for f in range(frames):
            # Full cycle, exact matching endpoints; preserve feet and all lower-body tracks.
            breath = math.sin(math.tau * f / (frames - 1))
            amplitude = {'spine':0.3, 'spine1':0.35, 'spine2':0.25, 'neck':-0.25, 'head':-0.2}.get(bone, 0.0)
            positions.append(base.translation)
            rotations.append(arm_rotations.get(bone, base.rotation) * unreal.Rotator(amplitude * breath, 0, 0).quaternion())
            scales.append(base.scale3d)
        assert controller.set_bone_track_keys(bone, positions, rotations, scales, False), bone
finally:
    controller.close_bracket(False)
assert unreal.EditorAssetLibrary.save_loaded_asset(target, False)
# Numeric pose checks catch copied crouch tracks, foot sliding, and dead/static breath.
checks = {}
for bone in ['hips','ctrl_cog','leftupleg','leftleg','leftfoot','rightupleg','rightleg','rightfoot']:
    poses = [unreal.AnimationLibrary.get_bone_pose_for_frame(target,bone,f,False) for f in [0,15,30,45,60]]
    p0 = poses[0]
    delta = max((p.translation-p0.translation).length() for p in poses)
    rotation_delta = max(abs(p.rotation.x-p0.rotation.x)+abs(p.rotation.y-p0.rotation.y)+abs(p.rotation.z-p0.rotation.z)+abs(p.rotation.w-p0.rotation.w) for p in poses)
    assert delta < 0.0001 and rotation_delta < 0.0001, (bone,delta,rotation_delta)
    checks[bone] = {'translationDelta':delta, 'rotationDelta':rotation_delta}
a = unreal.AnimationLibrary.get_bone_pose_for_frame(target,'spine1',15,False).rotation
b = unreal.AnimationLibrary.get_bone_pose_for_frame(target,'spine1',45,False).rotation
assert abs(a.x-b.x)+abs(a.y-b.y)+abs(a.z-b.z) > 0.001
assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).new_level_from_template(DEST+'/L_Character', MAP_SOURCE)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
character = next(a for a in actors if isinstance(a,unreal.SkeletalMeshActor))
component = character.get_component_by_class(unreal.SkeletalMeshComponent)
assert component.get_skeletal_mesh_asset().get_editor_property('skeleton') == target.get_editor_property('skeleton')
component.set_editor_property('animation_data', unreal.SingleAnimationPlayData(anim_to_play=target,saved_looping=True,saved_playing=True,saved_position=0.0,saved_play_rate=0.625))
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert unreal.EditorLoadingAndSavingUtils.save_map(world,DEST+'/L_Character')
report = {'status':'candidate-visual-QA-pending','humanApproved':False,'releaseEligible':False,'source':SOURCE,'fallbackMap':MAP_SOURCE,'map':DEST+'/L_Character','animation':target.get_path_name().split('.')[0],'skeleton':target.get_editor_property('skeleton').get_path_name(),'trackCount':len(names),'frames':frames,'playRate':0.625,'cycleSeconds':target.get_play_length()/0.625,'method':'arms lowered to 14.6 degrees from vertical in component space; lower body fixed; small breath', 'armMetrics':arm_metrics,'lowerBodyChecks':checks,'provenance':'user-supplied jaejae-v2 source, locally authored breath; no external donor','licenseStatus':'source license not independently certified; internal QA only','unchanged':['mesh','materials','camera','lighting'],'crouchRole':'preserved source, excluded from idle playback'}
(OUT/'build-report.json').write_text(json.dumps(report,indent=2)+'\n')
unreal.SystemLibrary.quit_editor()
