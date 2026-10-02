#include "Character/GahyeonCharacterPawn.h"
#include "Character/GahyeonHeroRuntimeSettings.h"

#include "AIController.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "UObject/ConstructorHelpers.h"
#include "Debug/GahyeonRuntimeDebugComponent.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/SpringArmComponent.h"
#include "Presentation/GahyeonCharacterPresentationComponent.h"
#include "Presentation/GahyeonConversationCameraComponent.h"
#include "Presentation/GahyeonMetaHumanFacialDriverComponent.h"
#include "World/GahyeonWorldActionComponent.h"
#include "Voice/GahyeonVoiceInputComponent.h"

AGahyeonCharacterPawn::AGahyeonCharacterPawn()
{
    PrimaryActorTick.bCanEverTick = false;
    SpawnCollisionHandlingMethod = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
    AIControllerClass = AAIController::StaticClass();
    bUseControllerRotationYaw = false;

    UCharacterMovementComponent* Movement = GetCharacterMovement();
    Movement->bOrientRotationToMovement = true;
    Movement->RotationRate = FRotator(0.0f, 360.0f, 0.0f);
    Movement->MaxWalkSpeed = 180.0f;
    Movement->BrakingDecelerationWalking = 600.0f;

    Presentation = CreateDefaultSubobject<UGahyeonCharacterPresentationComponent>(
        TEXT("GahyeonPresentation"));
    ConversationCamera = CreateDefaultSubobject<UGahyeonConversationCameraComponent>(
        TEXT("GahyeonConversationCamera"));
    MetaHumanFacialDriver = CreateDefaultSubobject<UGahyeonMetaHumanFacialDriverComponent>(
        TEXT("GahyeonMetaHumanFacialDriver"));
    VoiceInput = CreateDefaultSubobject<UGahyeonVoiceInputComponent>(
        TEXT("GahyeonVoiceInput"));
    Presentation->AddTickPrerequisiteComponent(VoiceInput);
    WorldActions = CreateDefaultSubobject<UGahyeonWorldActionComponent>(
        TEXT("GahyeonWorldActions"));
    RuntimeDebug = CreateDefaultSubobject<UGahyeonRuntimeDebugComponent>(
        TEXT("GahyeonRuntimeDebug"));

    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cylinder(
        TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(
        TEXT("/Engine/BasicShapes/Sphere.Sphere"));
    DiagnosticBody = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("DiagnosticBody"));
    DiagnosticBody->SetupAttachment(GetCapsuleComponent());
    DiagnosticBody->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    DiagnosticBody->SetRelativeLocation(FVector(0.0, 0.0, -5.0));
    DiagnosticBody->SetRelativeScale3D(FVector(0.42, 0.30, 1.20));
    if (Cylinder.Succeeded()) DiagnosticBody->SetStaticMesh(Cylinder.Object);

    DiagnosticHead = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("DiagnosticHead"));
    DiagnosticHead->SetupAttachment(GetCapsuleComponent());
    DiagnosticHead->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    DiagnosticHead->SetRelativeLocation(FVector(0.0, 0.0, 95.0));
    DiagnosticHead->SetRelativeScale3D(FVector(0.38));
    if (Sphere.Succeeded()) DiagnosticHead->SetStaticMesh(Sphere.Object);

    CameraBoom = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraBoom"));
    CameraBoom->SetupAttachment(GetCapsuleComponent());
    CameraBoom->TargetArmLength = 320.0f;
    CameraBoom->SetRelativeLocation(FVector(0.0, 0.0, 65.0));
    // Place the default Stage camera in front of the avatar, looking back at it.
    // Assembled MetaHuman visuals face +Y relative to the source pawn shell.
    // Place the desktop camera in front of that axis rather than on its side.
    CameraBoom->SetRelativeRotation(FRotator(-4.0f, -90.0f, 0.0f));
    CameraBoom->bUsePawnControlRotation = false;
    CameraBoom->bDoCollisionTest = false;
    CameraBoom->bEnableCameraLag = true;
    CameraBoom->CameraLagSpeed = 8.0f;

    FollowCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("FollowCamera"));
    FollowCamera->SetupAttachment(CameraBoom, USpringArmComponent::SocketName);
    FollowCamera->bUsePawnControlRotation = false;
    FollowCamera->FieldOfView = 58.0f;
}

void AGahyeonCharacterPawn::BeginPlay()
{
    Super::BeginPlay();
    const UGahyeonHeroRuntimeSettings* Settings = GetDefault<UGahyeonHeroRuntimeSettings>();
    if (!Settings->VisualActorClass.IsNull())
    {
        FString VisualError;
        const TSubclassOf<AActor> VisualClass = ResolveVisualActorClass(
            Settings->VisualActorClass, VisualError);
        if (VisualClass != nullptr)
        {
            for (TActorIterator<AActor> It(GetWorld(), VisualClass); It; ++It)
            {
                if (*It != this)
                {
                    VisualActor = *It;
                    SetActorTransform(VisualActor->GetActorTransform());
                    break;
                }
            }
            if (!IsValid(VisualActor))
            {
                FActorSpawnParameters Parameters;
                Parameters.SpawnCollisionHandlingOverride =
                    ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
                VisualActor = GetWorld()->SpawnActor<AActor>(
                    VisualClass, GetActorTransform(), Parameters);
                bOwnsVisualActor = IsValid(VisualActor);
                if (bOwnsVisualActor)
                {
                    VisualActor->AttachToActor(
                        this, FAttachmentTransformRules::KeepWorldTransform);
                }
            }
        }
        if (!IsValid(VisualActor))
        {
            const FString Message = VisualError.IsEmpty()
                ? FString::Printf(TEXT("Gahyeon visual actor unavailable: %s"),
                    *Settings->VisualActorClass.ToString())
                : VisualError;
            if (Settings->bRequireVisualActor)
            {
                UE_LOG(LogTemp, Fatal, TEXT("%s"), *Message);
            }
            UE_LOG(LogTemp, Warning, TEXT("%s"), *Message);
        }
        else
        {
            UE_LOG(LogTemp, Display,
                TEXT("Gahyeon visual actor ready: class=%s actor=%s owned=%s"),
                *Settings->VisualActorClass.ToString(),
                *VisualActor->GetName(),
                bOwnsVisualActor ? TEXT("true") : TEXT("false"));
        }
    }
    const bool bHasAvatar = IsValid(VisualActor)
        || (GetMesh() != nullptr && GetMesh()->GetSkeletalMeshAsset() != nullptr);
    DiagnosticBody->SetVisibility(!bHasAvatar, true);
    DiagnosticHead->SetVisibility(!bHasAvatar, true);
    if (!bHasAvatar)
    {
        GetCharacterMovement()->SetMovementMode(MOVE_Flying);
        RuntimeDebug->SetDrawOnScreen(bEnableDiagnosticOverlayWhenNoAvatar);
    }
}

TSubclassOf<AActor> AGahyeonCharacterPawn::ResolveVisualActorClass(
    const FSoftClassPath& VisualClassPath,
    FString& OutError)
{
    OutError.Reset();
    if (VisualClassPath.IsNull()) return nullptr;
    UClass* LoadedClass = VisualClassPath.TryLoadClass<AActor>();
    if (LoadedClass == nullptr || !LoadedClass->IsChildOf(AActor::StaticClass()))
    {
        OutError = FString::Printf(
            TEXT("not found or not an Actor subclass: %s"),
            *VisualClassPath.ToString());
        return nullptr;
    }
    return LoadedClass;
}

void AGahyeonCharacterPawn::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    if (bOwnsVisualActor && IsValid(VisualActor))
    {
        VisualActor->Destroy();
    }
    VisualActor = nullptr;
    bOwnsVisualActor = false;
    Super::EndPlay(EndPlayReason);
}
