#include "GahyeonMetaHumanQALibrary.h"

#include "Editor.h"
#include "MetaHumanIdentity.h"
#include "MetaHumanIdentityAssetEditorToolkit.h"
#include "MetaHumanIdentityCommands.h"
#include "MetaHumanIdentityParts.h"
#include "MetaHumanIdentityViewportSettings.h"
#include "MetaHumanCharacter.h"
#include "MetaHumanCharacterEditorSubsystem.h"
#include "LandmarkConfigIdentityHelper.h"
#include "MetaHumanContourDataVersion.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Subsystems/AssetEditorSubsystem.h"

bool UGahyeonMetaHumanQALibrary::ForceRefreshSkeletalMorphs(
    USkeletalMeshComponent* Component,
    FString& OutMessage)
{
    if (!IsValid(Component) || !Component->GetSkinnedAsset())
    {
        OutMessage = TEXT("skeletal mesh component or skinned asset is invalid");
        return false;
    }

    Component->TickAnimation(0.0f, false);
    Component->RefreshBoneTransforms();
    Component->MarkRenderDynamicDataDirty();
    OutMessage = TEXT("refreshed skeletal pose and morph render data");
    return true;
}

bool UGahyeonMetaHumanQALibrary::ConformCharacterFromIdentity(
    UObject* CharacterObject,
    UObject* IdentityObject,
    const bool bUseEyeMeshes,
    const bool bUseTeethMesh,
    FString& OutMessage)
{
    UMetaHumanCharacter* Character = Cast<UMetaHumanCharacter>(CharacterObject);
    const UMetaHumanIdentity* Identity = Cast<UMetaHumanIdentity>(IdentityObject);
    if (!Character || !Identity)
    {
        OutMessage = TEXT("character or identity has the wrong asset type");
        return false;
    }

    UMetaHumanCharacterEditorSubsystem* Subsystem = UMetaHumanCharacterEditorSubsystem::Get();
    if (!Subsystem || !Subsystem->TryAddObjectToEdit(Character))
    {
        OutMessage = TEXT("failed to register MetaHuman Character for editing");
        return false;
    }

    FImportFromIdentityParams Params;
    Params.bUseEyeMeshes = bUseEyeMeshes;
    Params.bUseTeethMesh = bUseTeethMesh;
    Params.bUseMetricScale = false;
    const EImportErrorCode Result = Subsystem->ImportFromIdentity(Character, Identity, Params);
    Subsystem->RemoveObjectToEdit(Character);
    if (Result != EImportErrorCode::Success)
    {
        OutMessage = FString::Printf(TEXT("MetaHuman Character import failed with code %d"), static_cast<int32>(Result));
        return false;
    }

    Character->MarkPackageDirty();
    OutMessage = TEXT("MetaHuman Character imported from conformed Identity");
    return true;
}

bool UGahyeonMetaHumanQALibrary::TrackAndConformIdentity(const FString& IdentityAssetPath, FString& OutMessage)
{
    UMetaHumanIdentity* Identity = LoadObject<UMetaHumanIdentity>(nullptr, *IdentityAssetPath);
    if (!Identity)
    {
        OutMessage = FString::Printf(TEXT("Identity not found: %s"), *IdentityAssetPath);
        UE_LOG(LogTemp, Error, TEXT("Gahyeon MetaHuman QA: %s"), *OutMessage);
        return false;
    }

    UMetaHumanIdentityFace* Face = Identity->FindPartOfClass<UMetaHumanIdentityFace>();
    if (!Face)
    {
        OutMessage = TEXT("Identity face component is missing");
        UE_LOG(LogTemp, Error, TEXT("Gahyeon MetaHuman QA: %s"), *OutMessage);
        return false;
    }

    UMetaHumanIdentityPose* NeutralPose = Face->FindPoseByType(EIdentityPoseType::Neutral);
    if (!NeutralPose)
    {
        OutMessage = TEXT("Identity neutral pose is missing");
        UE_LOG(LogTemp, Error, TEXT("Gahyeon MetaHuman QA: %s"), *OutMessage);
        return false;
    }

    if (NeutralPose->PromotedFrames.IsEmpty())
    {
        NeutralPose->Modify();
        int32 PromotedFrameIndex = INDEX_NONE;
        UMetaHumanIdentityPromotedFrame* PromotedFrame =
            NeutralPose->AddNewPromotedFrame(PromotedFrameIndex);
        if (!PromotedFrame || PromotedFrameIndex == INDEX_NONE)
        {
            OutMessage = TEXT("failed to create a promoted frame for the selected neutral pose");
            UE_LOG(LogTemp, Error, TEXT("Gahyeon MetaHuman QA: %s"), *OutMessage);
            return false;
        }
        PromotedFrame->bIsFrontView = true;
        FLandmarkConfigIdentityHelper InitialLandmarkConfig;
        const FIntRect InitialViewRect(
            0, 0,
            UMetaHumanIdentityPromotedFrame::DefaultTrackerImageSize.X,
            UMetaHumanIdentityPromotedFrame::DefaultTrackerImageSize.Y);
        FFrameTrackingContourData InitialContours =
            InitialLandmarkConfig.GetDefaultContourDataFromConfig(
                FVector2D(InitialViewRect.Width(), InitialViewRect.Height()),
                InitialLandmarkConfig.GetCurvePresetFromIdentityPose(NeutralPose->PoseType));
        PromotedFrame->InitializeMarkersFromParsedConfig(
            InitialContours, FMetaHumanContourDataVersion::GetContourDataVersionString());
        Identity->ViewportSettings->SetSelectedPromotedFrame(
            NeutralPose->PoseType, PromotedFrameIndex);
    }

    Identity->ViewportSettings->SelectedTreeNode = EIdentityTreeNodeIdentifier::FaceNeutralPose;
    UAssetEditorSubsystem* Editors = GEditor->GetEditorSubsystem<UAssetEditorSubsystem>();
    IAssetEditorInstance* Instance = Editors->FindEditorForAsset(Identity, true);
    if (!Instance)
    {
        Editors->OpenEditorForAsset(Identity);
        Instance = Editors->FindEditorForAsset(Identity, true);
    }
    if (!Instance || Instance->GetEditorName() != FName(TEXT("MetaHumanIdentityAssetEditorToolkit")))
    {
        OutMessage = TEXT("MetaHuman Identity editor is not ready");
        UE_LOG(LogTemp, Error, TEXT("Gahyeon MetaHuman QA: %s"), *OutMessage);
        return false;
    }

    FMetaHumanIdentityAssetEditorToolkit* Toolkit = static_cast<FMetaHumanIdentityAssetEditorToolkit*>(Instance);
    const FMetaHumanIdentityEditorCommands& Commands = FMetaHumanIdentityEditorCommands::Get();

    if (UMetaHumanIdentityCameraFrame* CameraFrame =
            Cast<UMetaHumanIdentityCameraFrame>(NeutralPose->PromotedFrames[0]))
    {
        const TMap<EIdentityPartMeshes, TArray<FVector>> Vertices =
            Face->GetConformalVerticesWorldPos(NeutralPose->PoseType);
        FBox TemplateBounds(ForceInit);
        for (const TPair<EIdentityPartMeshes, TArray<FVector>>& Part : Vertices)
        {
            for (const FVector& Vertex : Part.Value)
            {
                TemplateBounds += Vertex;
            }
        }
        if (!TemplateBounds.IsValid)
        {
            OutMessage = TEXT("MetaHuman conformal template bounds are invalid");
            UE_LOG(LogTemp, Error, TEXT("Gahyeon MetaHuman QA: %s"), *OutMessage);
            return false;
        }
        FBox ScanBounds(ForceInit);
        if (const UStaticMeshComponent* ScanComponent =
                Cast<UStaticMeshComponent>(NeutralPose->CaptureDataSceneComponent))
        {
            if (const UStaticMesh* ScanMesh = ScanComponent->GetStaticMesh())
            {
                ScanBounds = ScanMesh->GetBoundingBox().TransformBy(ScanComponent->GetComponentTransform());
            }
        }
        if (!ScanBounds.IsValid)
        {
            OutMessage = TEXT("Identity scan mesh bounds are invalid");
            UE_LOG(LogTemp, Error, TEXT("Gahyeon MetaHuman QA: %s"), *OutMessage);
            return false;
        }
        const FVector ScanCenter = ScanBounds.GetCenter();
        const FVector ScanSize = ScanBounds.GetSize();
        const double CameraDistance = FMath::Max(ScanSize.X, ScanSize.Z) * 1.8;
        CameraFrame->ViewLocation = FVector(
            ScanCenter.X, ScanBounds.Max.Y + CameraDistance, ScanCenter.Z);
        CameraFrame->ViewRotation = FRotator(0.0, -90.0, 0.0);
        CameraFrame->LookAtLocation = ScanCenter;
        CameraFrame->CameraViewFOV = 35.0f;
        CameraFrame->bIsNavigationLocked = true;
        if (FProperty* CameraProperty = UMetaHumanIdentityCameraFrame::StaticClass()->
                FindPropertyByName(GET_MEMBER_NAME_CHECKED(UMetaHumanIdentityCameraFrame, ViewLocation)))
        {
            FPropertyChangedEvent CameraChanged(CameraProperty);
            CameraFrame->PostEditChangeProperty(CameraChanged);
        }
        FLandmarkConfigIdentityHelper LandmarkConfig;
        const FIntRect ViewRect(
            0, 0,
            UMetaHumanIdentityPromotedFrame::DefaultTrackerImageSize.X,
            UMetaHumanIdentityPromotedFrame::DefaultTrackerImageSize.Y);
        const ECurvePresetType CurvePreset =
            LandmarkConfig.GetCurvePresetFromIdentityPose(NeutralPose->PoseType);
        FFrameTrackingContourData Contours =
            LandmarkConfig.GetDefaultContourDataFromConfig(
                FVector2D(ViewRect.Width(), ViewRect.Height()), CurvePreset);
        for (TPair<FString, FTrackingContour>& Contour : Contours.TrackingContours)
        {
            Contour.Value.State.bVisible = true;
            Contour.Value.State.bActive = true;
        }
        int32 ProjectedPointCount = 0;
        for (const TPair<FString, FTrackingContour>& Contour : Contours.TrackingContours)
        {
            ProjectedPointCount += Contour.Value.DensePoints.Num();
        }
        UE_LOG(LogTemp, Display,
            TEXT("Gahyeon MetaHuman QA projected contours: curves=%d points=%d containsData=%s containsActive=%s"),
            Contours.TrackingContours.Num(), ProjectedPointCount,
            Contours.ContainsData() ? TEXT("true") : TEXT("false"),
            Contours.ContainsActiveData() ? TEXT("true") : TEXT("false"));
        CameraFrame->InitializeMarkersFromParsedConfig(
            Contours, FMetaHumanContourDataVersion::GetContourDataVersionString());
        UE_LOG(LogTemp, Display, TEXT("Gahyeon MetaHuman QA template bounds: %s"),
            *TemplateBounds.ToString());
        UE_LOG(LogTemp, Display, TEXT("Gahyeon MetaHuman QA scan bounds: %s"),
            *ScanBounds.ToString());
        UE_LOG(LogTemp, Display,
            TEXT("Gahyeon MetaHuman QA camera: location=%s rotation=%s lookAt=%s fov=%.2f front=%s canTrack=%s activeBefore=%s"),
            *CameraFrame->ViewLocation.ToString(), *CameraFrame->ViewRotation.ToString(),
            *CameraFrame->LookAtLocation.ToString(), CameraFrame->CameraViewFOV,
            CameraFrame->bIsFrontView ? TEXT("true") : TEXT("false"),
            CameraFrame->CanTrack() ? TEXT("true") : TEXT("false"),
            CameraFrame->FrameContoursContainActiveData() ? TEXT("true") : TEXT("false"));
    }

    Identity->SetBlockingProcessing(true);
    if (!Commands.TrackCurrent.IsValid() ||
        !Toolkit->GetToolkitCommands()->CanExecuteAction(Commands.TrackCurrent.ToSharedRef()) ||
        !Toolkit->GetToolkitCommands()->TryExecuteAction(Commands.TrackCurrent.ToSharedRef()))
    {
        OutMessage = TEXT("Track Markers command is not executable for the active promoted frame");
        UE_LOG(LogTemp, Error, TEXT("Gahyeon MetaHuman QA: %s"), *OutMessage);
        return false;
    }

    UE_LOG(LogTemp, Display,
        TEXT("Gahyeon MetaHuman QA diagnostics: promoted=%d validContourFrames=%d activeAfter=%s"),
        NeutralPose->PromotedFrames.Num(), NeutralPose->GetValidContourDataFramesFrontFirst().Num(),
        NeutralPose->PromotedFrames[0]->FrameContoursContainActiveData() ? TEXT("true") : TEXT("false"));

    if (NeutralPose->GetValidContourDataFramesFrontFirst().IsEmpty())
    {
        OutMessage = TEXT("Tracking produced no valid contour frame; camera framing or marker correction is required");
        UE_LOG(LogTemp, Error, TEXT("Gahyeon MetaHuman QA: %s"), *OutMessage);
        return false;
    }

    const EIdentityErrorCode Result = Face->Conform();
    if ((Result != EIdentityErrorCode::None && !IsIdentityErrorCodeWarningOnly(Result)) ||
        !Face->bIsConformed)
    {
        OutMessage = FString::Printf(TEXT("MetaHuman conform failed with code %d"), static_cast<int32>(Result));
        UE_LOG(LogTemp, Error, TEXT("Gahyeon MetaHuman QA: %s"), *OutMessage);
        return false;
    }

    Identity->MarkPackageDirty();
    OutMessage = Result == EIdentityErrorCode::None
        ? TEXT("Tracked active frame and conformed MetaHuman Identity")
        : FString::Printf(
            TEXT("Tracked and conformed MetaHuman Identity with warning code %d"),
            static_cast<int32>(Result));
    return true;
}
