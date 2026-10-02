#pragma once

#include "Components/ActorComponent.h"
#include "GahyeonLiveSpeechCaptureComponent.generated.h"

class UGahyeonRuntimeSubsystem;

/** Opt-in rendered evidence capture at an actually presented speech-viseme frame. */
UCLASS(ClassGroup = (Gahyeon))
class GAHYEONSTAGE_API UGahyeonLiveSpeechCaptureComponent final : public UActorComponent
{
    GENERATED_BODY()

public:
    UGahyeonLiveSpeechCaptureComponent();
    virtual void BeginPlay() override;
    virtual void TickComponent(
        float DeltaTime,
        ELevelTick TickType,
        FActorComponentTickFunction* ThisTickFunction) override;

private:
    void WriteEvidence(bool bScreenshotPresent);

    UPROPERTY(Transient)
    TObjectPtr<UGahyeonRuntimeSubsystem> Runtime;

    FString ScreenshotPath;
    FString EvidencePath;
    FString CapturedViseme;
    double CapturedWeight = 0.0;
    int64 CapturedGeneration = 0;
    bool bEnabled = false;
    bool bRequested = false;
    bool bFinalEvidenceWritten = false;
    double StrongVisemeSinceSeconds = -1.0;
    double CapturedAppliedJawOpen = 0.0;
    bool bCapturedFaceRigReady = false;
};
