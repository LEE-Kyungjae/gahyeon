#pragma once

#include "Components/ActorComponent.h"
#include "GahyeonMetaHumanFacialDriverComponent.generated.h"

class UControlRigComponent;
class UGahyeonRuntimeSubsystem;
class USkeletalMeshComponent;

/**
 * Character-local bridge from Core semantic visemes to a real MetaHuman Face Control Rig.
 * The rig class remains configuration, so another personality/avatar can replace it without
 * changing Core or the semantic speech contract.
 */
UCLASS(ClassGroup=(Gahyeon), meta=(BlueprintSpawnableComponent))
class GAHYEONSTAGE_API UGahyeonMetaHumanFacialDriverComponent final
    : public UActorComponent
{
    GENERATED_BODY()

public:
    UGahyeonMetaHumanFacialDriverComponent();

    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
    virtual void TickComponent(
        float DeltaTime,
        ELevelTick TickType,
        FActorComponentTickFunction* ThisTickFunction) override;

    UFUNCTION(BlueprintPure, Category="Gahyeon|Face")
    bool IsFaceRigReady() const { return bFaceRigReady; }

    UFUNCTION(BlueprintPure, Category="Gahyeon|Face")
    USkeletalMeshComponent* GetDrivenFaceMesh() const { return FaceMesh.Get(); }

    UFUNCTION(BlueprintPure, Category="Gahyeon|Face")
    float GetAppliedJawOpen() const;

private:
    bool TryInitializeFaceRig();
    void BuildSemanticTargets(
        const FString& PrimaryViseme,
        double PrimaryWeight,
        const FString& SecondaryViseme,
        double SecondaryWeight,
        double JawOpen,
        double Blink);
    void AccumulateViseme(const FString& Semantic, float Weight);
    void AddTarget(FName Control, float Weight);
    bool SetRigValue(FName Element, float Weight);
    void ResetFaceState();

    UPROPERTY(Transient)
    TObjectPtr<UGahyeonRuntimeSubsystem> Runtime;

    UPROPERTY(Transient)
    TObjectPtr<UControlRigComponent> FaceRig;

    TWeakObjectPtr<USkeletalMeshComponent> FaceMesh;
    TMap<FName, float> CurrentWeights;
    TMap<FName, float> TargetWeights;
    bool bFaceRigReady = false;
    double NextInitializationAttemptSeconds = 0.0;
};
