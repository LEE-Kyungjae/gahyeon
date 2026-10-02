#include "Presentation/GahyeonConversationCameraComponent.h"

#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/SpringArmComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Runtime/GahyeonRuntimeSubsystem.h"

UGahyeonConversationCameraComponent::UGahyeonConversationCameraComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.bStartWithTickEnabled = true;
    PrimaryComponentTick.TickGroup = TG_PostUpdateWork;
}

void UGahyeonConversationCameraComponent::BeginPlay()
{
    Super::BeginPlay();
    CameraBoom = GetOwner() != nullptr
        ? GetOwner()->FindComponentByClass<USpringArmComponent>() : nullptr;
    if (UWorld* World = GetWorld())
    {
        if (APlayerController* Controller = UGameplayStatics::GetPlayerController(World, 0))
        {
            if (AActor* Owner = GetOwner())
            {
                Controller->SetViewTargetWithBlend(Owner, 0.0f);
                bClaimedViewTarget = Controller->GetViewTarget() == Owner;
            }
        }
    }
    if (UGameInstance* GameInstance = GetWorld() != nullptr
        ? GetWorld()->GetGameInstance() : nullptr)
    {
        Runtime = GameInstance->GetSubsystem<UGahyeonRuntimeSubsystem>();
    }
}

void UGahyeonConversationCameraComponent::TickComponent(
    float DeltaTime,
    ELevelTick TickType,
    FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
    UWorld* World = GetWorld();
    if (Runtime == nullptr || CameraBoom == nullptr || World == nullptr) return;

    if (!bClaimedViewTarget)
    {
        if (APlayerController* Controller = UGameplayStatics::GetPlayerController(World, 0))
        {
            if (AActor* Owner = GetOwner())
            {
                Controller->SetViewTargetWithBlend(Owner, 0.0f);
                bClaimedViewTarget = Controller->GetViewTarget() == Owner;
            }
        }
    }

    const FString Phase = Runtime->GetSnapshot().ConversationPhase;
    const bool bConversationEngaged = Phase == TEXT("listening")
        || Phase == TEXT("thinking") || Phase == TEXT("speaking")
        || Phase == TEXT("reacting");
    const double Now = World->GetTimeSeconds();
    if (bConversationEngaged)
    {
        ReturnAfterSeconds = Now + ReturnDelaySeconds;
    }
    else if (bWasConversationEngaged)
    {
        ReturnAfterSeconds = FMath::Max(ReturnAfterSeconds, Now + ReturnDelaySeconds);
    }
    bWasConversationEngaged = bConversationEngaged;
    const bool bUseBust = bConversationEngaged || Now < ReturnAfterSeconds;

    const float TargetLength = bUseBust ? BustArmLength : FullBodyArmLength;
    const float TargetHeight = bUseBust ? BustHeight : FullBodyHeight;
    CameraBoom->TargetArmLength = FMath::FInterpTo(
        CameraBoom->TargetArmLength, TargetLength, DeltaTime, TransitionSpeed);
    FVector Location = CameraBoom->GetRelativeLocation();
    Location.Z = FMath::FInterpTo(Location.Z, TargetHeight, DeltaTime, TransitionSpeed);
    CameraBoom->SetRelativeLocation(Location);
}
