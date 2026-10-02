#pragma once

#include "Components/ActorComponent.h"
#include "GahyeonConversationCameraComponent.generated.h"

class UGahyeonRuntimeSubsystem;
class USpringArmComponent;

/** Smooth full-body ↔ bust framing driven by the persistent conversation phase. */
UCLASS(ClassGroup = (Gahyeon), meta = (BlueprintSpawnableComponent))
class GAHYEONSTAGE_API UGahyeonConversationCameraComponent final : public UActorComponent
{
    GENERATED_BODY()

public:
    UGahyeonConversationCameraComponent();
    virtual void BeginPlay() override;
    virtual void TickComponent(
        float DeltaTime,
        ELevelTick TickType,
        FActorComponentTickFunction* ThisTickFunction) override;

private:
    UPROPERTY(Transient)
    TObjectPtr<UGahyeonRuntimeSubsystem> Runtime;

    UPROPERTY(Transient)
    TObjectPtr<USpringArmComponent> CameraBoom;

    UPROPERTY(EditAnywhere, Category = "Gahyeon|Camera")
    float FullBodyArmLength = 320.0f;

    UPROPERTY(EditAnywhere, Category = "Gahyeon|Camera")
    float BustArmLength = 115.0f;

    UPROPERTY(EditAnywhere, Category = "Gahyeon|Camera")
    float FullBodyHeight = 65.0f;

    UPROPERTY(EditAnywhere, Category = "Gahyeon|Camera")
    float BustHeight = 160.0f;

    UPROPERTY(EditAnywhere, Category = "Gahyeon|Camera")
    float TransitionSpeed = 4.5f;

    UPROPERTY(EditAnywhere, Category = "Gahyeon|Camera")
    float ReturnDelaySeconds = 2.5f;

    double ReturnAfterSeconds = 0.0;
    bool bWasConversationEngaged = false;
    bool bClaimedViewTarget = false;
};
