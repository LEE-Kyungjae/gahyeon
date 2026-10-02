#pragma once

#include "GameFramework/Character.h"
#include "GahyeonCharacterPawn.generated.h"

class UGahyeonCharacterPresentationComponent;
class UGahyeonConversationCameraComponent;
class UGahyeonMetaHumanFacialDriverComponent;
class UGahyeonRuntimeDebugComponent;
class UGahyeonWorldActionComponent;
class UGahyeonVoiceInputComponent;
class UCameraComponent;
class USpringArmComponent;
class UStaticMeshComponent;
class AActor;

/** Placeable source-only character shell; MetaHuman/custom mesh can replace inherited Mesh. */
UCLASS(Blueprintable)
class GAHYEONSTAGE_API AGahyeonCharacterPawn : public ACharacter
{
    GENERATED_BODY()

public:
    AGahyeonCharacterPawn();

    static TSubclassOf<AActor> ResolveVisualActorClass(
        const FSoftClassPath& VisualClassPath,
        FString& OutError);

    UFUNCTION(BlueprintPure, Category = "Gahyeon")
    UGahyeonCharacterPresentationComponent* GetPresentation() const { return Presentation; }

    UFUNCTION(BlueprintPure, Category = "Gahyeon")
    UGahyeonWorldActionComponent* GetWorldActions() const { return WorldActions; }

    UFUNCTION(BlueprintPure, Category = "Gahyeon")
    UGahyeonRuntimeDebugComponent* GetRuntimeDebug() const { return RuntimeDebug; }

    UFUNCTION(BlueprintPure, Category = "Gahyeon")
    UGahyeonVoiceInputComponent* GetVoiceInput() const { return VoiceInput; }

    /** Assembled MetaHuman/custom visual hosted without reparenting its Blueprint. */
    UFUNCTION(BlueprintPure, Category = "Gahyeon")
    AActor* GetVisualActor() const { return VisualActor; }

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Gahyeon", meta = (AllowPrivateAccess = "true"))
    TObjectPtr<UGahyeonCharacterPresentationComponent> Presentation;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Gahyeon|Camera", meta = (AllowPrivateAccess = "true"))
    TObjectPtr<UGahyeonConversationCameraComponent> ConversationCamera;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Gahyeon|Face", meta = (AllowPrivateAccess = "true"))
    TObjectPtr<UGahyeonMetaHumanFacialDriverComponent> MetaHumanFacialDriver;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Gahyeon", meta = (AllowPrivateAccess = "true"))
    TObjectPtr<UGahyeonWorldActionComponent> WorldActions;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Gahyeon", meta = (AllowPrivateAccess = "true"))
    TObjectPtr<UGahyeonRuntimeDebugComponent> RuntimeDebug;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Gahyeon", meta = (AllowPrivateAccess = "true"))
    TObjectPtr<UGahyeonVoiceInputComponent> VoiceInput;

    /** Source-only diagnostic geometry; hidden automatically when a skeletal avatar is assigned. */
    UPROPERTY(VisibleAnywhere, Category = "Gahyeon|Diagnostic")
    TObjectPtr<UStaticMeshComponent> DiagnosticBody;

    UPROPERTY(VisibleAnywhere, Category = "Gahyeon|Diagnostic")
    TObjectPtr<UStaticMeshComponent> DiagnosticHead;

    UPROPERTY(VisibleAnywhere, Category = "Gahyeon|Camera")
    TObjectPtr<USpringArmComponent> CameraBoom;

    UPROPERTY(VisibleAnywhere, Category = "Gahyeon|Camera")
    TObjectPtr<UCameraComponent> FollowCamera;

    UPROPERTY(EditDefaultsOnly, Category = "Gahyeon|Diagnostic")
    bool bEnableDiagnosticOverlayWhenNoAvatar = true;

    UPROPERTY(Transient)
    TObjectPtr<AActor> VisualActor;

    bool bOwnsVisualActor = false;
};
