#include "Presentation/GahyeonMetaHumanFacialDriverComponent.h"

#include "Character/GahyeonCharacterPawn.h"
#include "Character/GahyeonHeroRuntimeSettings.h"
#include "Components/SkeletalMeshComponent.h"
#include "ControlRig.h"
#include "ControlRigComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Rigs/RigHierarchy.h"
#include "Runtime/GahyeonRuntimeSubsystem.h"

namespace
{
constexpr float FacialInterpolationSpeed = 18.0f;

const FName JawOpen(TEXT("CTRL_expressions_jawOpen"));
const FName BlinkLeft(TEXT("CTRL_expressions_eyeBlinkL"));
const FName BlinkRight(TEXT("CTRL_expressions_eyeBlinkR"));
const FName CornerPullLeft(TEXT("CTRL_expressions_mouthCornerPullL"));
const FName CornerPullRight(TEXT("CTRL_expressions_mouthCornerPullR"));
const FName FunnelUpperLeft(TEXT("CTRL_expressions_mouthFunnelUL"));
const FName FunnelUpperRight(TEXT("CTRL_expressions_mouthFunnelUR"));
const FName FunnelDownLeft(TEXT("CTRL_expressions_mouthFunnelDL"));
const FName FunnelDownRight(TEXT("CTRL_expressions_mouthFunnelDR"));
const FName PurseUpperLeft(TEXT("CTRL_expressions_mouthLipsPurseUL"));
const FName PurseUpperRight(TEXT("CTRL_expressions_mouthLipsPurseUR"));
const FName PurseDownLeft(TEXT("CTRL_expressions_mouthLipsPurseDL"));
const FName PurseDownRight(TEXT("CTRL_expressions_mouthLipsPurseDR"));
const FName TogetherUpperLeft(TEXT("CTRL_expressions_mouthLipsTogetherUL"));
const FName TogetherUpperRight(TEXT("CTRL_expressions_mouthLipsTogetherUR"));
const FName TogetherDownLeft(TEXT("CTRL_expressions_mouthLipsTogetherDL"));
const FName TogetherDownRight(TEXT("CTRL_expressions_mouthLipsTogetherDR"));
const FName LowerLipBiteLeft(TEXT("CTRL_expressions_mouthLowerLipBiteL"));
const FName LowerLipBiteRight(TEXT("CTRL_expressions_mouthLowerLipBiteR"));
const FName LowerLipDepressLeft(TEXT("CTRL_expressions_mouthLowerLipDepressL"));
const FName LowerLipDepressRight(TEXT("CTRL_expressions_mouthLowerLipDepressR"));

FName ResolveGuiControl(const FName Expression)
{
    static const TMap<FName, FName> Controls = {
        {BlinkLeft, TEXT("CTRL_L_eye_blink")},
        {BlinkRight, TEXT("CTRL_R_eye_blink")},
        {CornerPullLeft, TEXT("CTRL_L_mouth_cornerPull")},
        {CornerPullRight, TEXT("CTRL_R_mouth_cornerPull")},
        {FunnelUpperLeft, TEXT("CTRL_L_mouth_funnelU")},
        {FunnelUpperRight, TEXT("CTRL_R_mouth_funnelU")},
        {FunnelDownLeft, TEXT("CTRL_L_mouth_funnelD")},
        {FunnelDownRight, TEXT("CTRL_R_mouth_funnelD")},
        {PurseUpperLeft, TEXT("CTRL_L_mouth_purseU")},
        {PurseUpperRight, TEXT("CTRL_R_mouth_purseU")},
        {PurseDownLeft, TEXT("CTRL_L_mouth_purseD")},
        {PurseDownRight, TEXT("CTRL_R_mouth_purseD")},
        {TogetherUpperLeft, TEXT("CTRL_L_mouth_lipsTogetherU")},
        {TogetherUpperRight, TEXT("CTRL_R_mouth_lipsTogetherU")},
        {TogetherDownLeft, TEXT("CTRL_L_mouth_lipsTogetherD")},
        {TogetherDownRight, TEXT("CTRL_R_mouth_lipsTogetherD")},
        {LowerLipBiteLeft, TEXT("CTRL_L_mouth_lipBiteD")},
        {LowerLipBiteRight, TEXT("CTRL_R_mouth_lipBiteD")},
        {LowerLipDepressLeft, TEXT("CTRL_L_mouth_lowerLipDepress")},
        {LowerLipDepressRight, TEXT("CTRL_R_mouth_lowerLipDepress")},
    };
    const FName* Match = Controls.Find(Expression);
    return Match != nullptr ? *Match : NAME_None;
}
}

UGahyeonMetaHumanFacialDriverComponent::UGahyeonMetaHumanFacialDriverComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.bStartWithTickEnabled = true;
    PrimaryComponentTick.TickGroup = TG_PostPhysics;
}

float UGahyeonMetaHumanFacialDriverComponent::GetAppliedJawOpen() const
{
    return CurrentWeights.FindRef(JawOpen);
}

void UGahyeonMetaHumanFacialDriverComponent::BeginPlay()
{
    Super::BeginPlay();
    if (UGameInstance* GameInstance = GetWorld() != nullptr
        ? GetWorld()->GetGameInstance() : nullptr)
    {
        Runtime = GameInstance->GetSubsystem<UGahyeonRuntimeSubsystem>();
    }
}

void UGahyeonMetaHumanFacialDriverComponent::EndPlay(
    const EEndPlayReason::Type EndPlayReason)
{
    ResetFaceState();
    if (IsValid(FaceRig))
    {
        FaceRig->ClearMappedElements();
        FaceRig->DestroyComponent();
    }
    FaceRig = nullptr;
    FaceMesh.Reset();
    Runtime = nullptr;
    bFaceRigReady = false;
    Super::EndPlay(EndPlayReason);
}

bool UGahyeonMetaHumanFacialDriverComponent::TryInitializeFaceRig()
{
    UWorld* World = GetWorld();
    if (World == nullptr || GetOwner() == nullptr) return false;
    const double Now = World->GetTimeSeconds();
    if (Now < NextInitializationAttemptSeconds) return false;
    NextInitializationAttemptSeconds = Now + 0.5;

    const AGahyeonCharacterPawn* Pawn = Cast<AGahyeonCharacterPawn>(GetOwner());
    AActor* VisualActor = Pawn != nullptr ? Pawn->GetVisualActor() : GetOwner();
    if (!IsValid(VisualActor)) return false;

    TArray<USkeletalMeshComponent*> Meshes;
    VisualActor->GetComponents<USkeletalMeshComponent>(Meshes);
    USkeletalMeshComponent* ResolvedFace = nullptr;
    for (USkeletalMeshComponent* Mesh : Meshes)
    {
        if (IsValid(Mesh) && Mesh->GetSkeletalMeshAsset() != nullptr
            && Mesh->GetName().Contains(TEXT("Face")))
        {
            ResolvedFace = Mesh;
            break;
        }
    }
    if (ResolvedFace == nullptr) return false;

    const FSoftClassPath RigPath = GetDefault<UGahyeonHeroRuntimeSettings>()->FacialControlRigClass;
    UClass* RigClass = RigPath.TryLoadClass<UControlRig>();
    if (RigClass == nullptr || !RigClass->IsChildOf(UControlRig::StaticClass()))
    {
        UE_LOG(LogTemp, Error, TEXT("Gahyeon face Control Rig unavailable: %s"),
            *RigPath.ToString());
        SetComponentTickEnabled(false);
        return false;
    }

    FaceRig = NewObject<UControlRigComponent>(GetOwner(), TEXT("GahyeonLiveFaceControlRig"));
    if (!IsValid(FaceRig)) return false;
    FaceRig->RegisterComponent();
    FaceRig->SetControlRigClass(RigClass);
    FaceRig->AddMappedCompleteSkeletalMesh(
        ResolvedFace, EControlRigComponentMapDirection::Output);
    FaceRig->Initialize();
    FaceMesh = ResolvedFace;
    bFaceRigReady = true;
    UControlRig* ControlRig = FaceRig->GetControlRig();
    URigHierarchy* Hierarchy = ControlRig != nullptr ? ControlRig->GetHierarchy() : nullptr;
    const bool bJawIsControl = Hierarchy != nullptr
        && Hierarchy->Find<FRigControlElement>(FRigElementKey(JawOpen, ERigElementType::Control));
    const bool bJawIsCurve = Hierarchy != nullptr
        && Hierarchy->Find<FRigCurveElement>(FRigElementKey(JawOpen, ERigElementType::Curve));
    UE_LOG(LogTemp, Display,
        TEXT("Gahyeon live MetaHuman face rig ready: mesh=%s rig=%s jawControl=%s jawCurve=%s"),
        *ResolvedFace->GetName(), *RigPath.ToString(),
        bJawIsControl ? TEXT("true") : TEXT("false"),
        bJawIsCurve ? TEXT("true") : TEXT("false"));
    return true;
}

void UGahyeonMetaHumanFacialDriverComponent::AddTarget(FName Control, float Weight)
{
    float& Existing = TargetWeights.FindOrAdd(Control);
    Existing = FMath::Clamp(Existing + Weight, 0.0f, 1.0f);
}

void UGahyeonMetaHumanFacialDriverComponent::AccumulateViseme(
    const FString& Semantic, float Weight)
{
    if (Weight <= KINDA_SMALL_NUMBER || Semantic.IsEmpty()) return;
    const FString Shape = Semantic.ToUpper();
    if (Shape == TEXT("AA") || Shape == TEXT("A"))
    {
        AddTarget(JawOpen, Weight * 0.88f);
        AddTarget(LowerLipDepressLeft, Weight * 0.24f);
        AddTarget(LowerLipDepressRight, Weight * 0.24f);
    }
    else if (Shape == TEXT("E") || Shape == TEXT("I"))
    {
        AddTarget(JawOpen, Weight * 0.38f);
        AddTarget(CornerPullLeft, Weight * 0.55f);
        AddTarget(CornerPullRight, Weight * 0.55f);
    }
    else if (Shape == TEXT("O") || Shape == TEXT("U"))
    {
        AddTarget(JawOpen, Weight * (Shape == TEXT("O") ? 0.55f : 0.34f));
        const float Funnel = Weight * (Shape == TEXT("O") ? 0.72f : 0.48f);
        AddTarget(FunnelUpperLeft, Funnel);
        AddTarget(FunnelUpperRight, Funnel);
        AddTarget(FunnelDownLeft, Funnel);
        AddTarget(FunnelDownRight, Funnel);
        if (Shape == TEXT("U"))
        {
            AddTarget(PurseUpperLeft, Weight * 0.58f);
            AddTarget(PurseUpperRight, Weight * 0.58f);
            AddTarget(PurseDownLeft, Weight * 0.58f);
            AddTarget(PurseDownRight, Weight * 0.58f);
        }
    }
    else if (Shape == TEXT("FV") || Shape == TEXT("F") || Shape == TEXT("V"))
    {
        AddTarget(LowerLipBiteLeft, Weight * 0.72f);
        AddTarget(LowerLipBiteRight, Weight * 0.72f);
    }
    else if (Shape == TEXT("MBP") || Shape == TEXT("M")
        || Shape == TEXT("B") || Shape == TEXT("P"))
    {
        AddTarget(TogetherUpperLeft, Weight * 0.82f);
        AddTarget(TogetherUpperRight, Weight * 0.82f);
        AddTarget(TogetherDownLeft, Weight * 0.82f);
        AddTarget(TogetherDownRight, Weight * 0.82f);
    }
    else
    {
        AddTarget(JawOpen, Weight * 0.42f);
    }
}

void UGahyeonMetaHumanFacialDriverComponent::BuildSemanticTargets(
    const FString& PrimaryViseme,
    double PrimaryWeight,
    const FString& SecondaryViseme,
    double SecondaryWeight,
    double InJawOpen,
    double Blink)
{
    TargetWeights.Reset();
    AccumulateViseme(PrimaryViseme, static_cast<float>(PrimaryWeight));
    AccumulateViseme(SecondaryViseme, static_cast<float>(SecondaryWeight));
    AddTarget(JawOpen, static_cast<float>(FMath::Clamp(InJawOpen, 0.0, 1.0)) * 0.35f);
    AddTarget(BlinkLeft, static_cast<float>(FMath::Clamp(Blink, 0.0, 1.0)));
    AddTarget(BlinkRight, static_cast<float>(FMath::Clamp(Blink, 0.0, 1.0)));
}

void UGahyeonMetaHumanFacialDriverComponent::ResetFaceState()
{
    if (IsValid(FaceRig))
    {
        for (const TPair<FName, float>& Pair : CurrentWeights)
        {
            SetRigValue(Pair.Key, 0.0f);
        }
        FaceRig->Update(0.0f);
    }
    CurrentWeights.Reset();
    TargetWeights.Reset();
}

bool UGahyeonMetaHumanFacialDriverComponent::SetRigValue(FName Element, float Weight)
{
    if (!IsValid(FaceRig)) return false;
    UControlRig* ControlRig = FaceRig->GetControlRig();
    URigHierarchy* Hierarchy = ControlRig != nullptr ? ControlRig->GetHierarchy() : nullptr;
    if (Hierarchy == nullptr) return false;
    if (Element == JawOpen)
    {
        const FName JawControl(TEXT("CTRL_C_jaw"));
        if (Hierarchy->Find<FRigControlElement>(
            FRigElementKey(JawControl, ERigElementType::Control)))
        {
            FaceRig->SetControlVector2D(JawControl, FVector2D(0.0, -Weight));
            return true;
        }
    }
    const FName GuiControl = ResolveGuiControl(Element);
    if (!GuiControl.IsNone() && Hierarchy->Find<FRigControlElement>(
        FRigElementKey(GuiControl, ERigElementType::Control)))
    {
        FaceRig->SetControlFloat(GuiControl, Weight);
        return true;
    }
    if (Hierarchy->Find<FRigControlElement>(FRigElementKey(Element, ERigElementType::Control)))
    {
        FaceRig->SetControlFloat(Element, Weight);
        return true;
    }
    const FRigElementKey CurveKey(Element, ERigElementType::Curve);
    if (Hierarchy->Find<FRigCurveElement>(CurveKey))
    {
        Hierarchy->SetCurveValue(CurveKey, Weight);
        return true;
    }
    return false;
}

void UGahyeonMetaHumanFacialDriverComponent::TickComponent(
    float DeltaTime,
    ELevelTick TickType,
    FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
    if (Runtime == nullptr)
    {
        if (UGameInstance* GameInstance = GetWorld() != nullptr
            ? GetWorld()->GetGameInstance() : nullptr)
        {
            Runtime = GameInstance->GetSubsystem<UGahyeonRuntimeSubsystem>();
        }
    }
    if (!bFaceRigReady && !TryInitializeFaceRig()) return;
    if (Runtime == nullptr || !IsValid(FaceRig) || !FaceMesh.IsValid()) return;

    const FGahyeonRuntimeFrameSnapshot Frame = Runtime->GetSnapshot();
    BuildSemanticTargets(
        Frame.PrimaryViseme, Frame.PrimaryVisemeWeight,
        Frame.SecondaryViseme, Frame.SecondaryVisemeWeight,
        Frame.JawOpen, Frame.Blink);

    TSet<FName> Controls;
    for (const TPair<FName, float>& Pair : CurrentWeights) Controls.Add(Pair.Key);
    for (const TPair<FName, float>& Pair : TargetWeights) Controls.Add(Pair.Key);
    for (const FName Control : Controls)
    {
        const float Current = CurrentWeights.FindRef(Control);
        const float Target = TargetWeights.FindRef(Control);
        const float Smoothed = FMath::FInterpTo(
            Current, Target, DeltaTime, FacialInterpolationSpeed);
        SetRigValue(Control, Smoothed);
        if (Smoothed > 0.001f || Target > 0.001f)
        {
            CurrentWeights.Add(Control, Smoothed);
        }
        else
        {
            CurrentWeights.Remove(Control);
        }
    }
    FaceRig->Update(DeltaTime);
}
