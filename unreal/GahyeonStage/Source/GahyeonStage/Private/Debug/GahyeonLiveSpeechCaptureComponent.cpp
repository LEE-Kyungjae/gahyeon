#include "Debug/GahyeonLiveSpeechCaptureComponent.h"

#include "Character/GahyeonCharacterPawn.h"
#include "Dom/JsonObject.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Runtime/GahyeonRuntimeSubsystem.h"
#include "Presentation/GahyeonMetaHumanFacialDriverComponent.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "UnrealClient.h"

UGahyeonLiveSpeechCaptureComponent::UGahyeonLiveSpeechCaptureComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.bStartWithTickEnabled = true;
}

void UGahyeonLiveSpeechCaptureComponent::BeginPlay()
{
    Super::BeginPlay();
    bEnabled = FParse::Value(
        FCommandLine::Get(), TEXT("GahyeonLiveSpeechCapture="), ScreenshotPath)
        && FParse::Value(
            FCommandLine::Get(), TEXT("GahyeonLiveSpeechEvidence="), EvidencePath)
        && !ScreenshotPath.IsEmpty() && !EvidencePath.IsEmpty();
    if (!bEnabled)
    {
        SetComponentTickEnabled(false);
        return;
    }
    ScreenshotPath = FPaths::ConvertRelativePathToFull(ScreenshotPath);
    EvidencePath = FPaths::ConvertRelativePathToFull(EvidencePath);
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(ScreenshotPath), true);
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(EvidencePath), true);
    IFileManager::Get().Delete(*ScreenshotPath, false, true, true);
    if (UGameInstance* GameInstance = GetWorld() != nullptr
        ? GetWorld()->GetGameInstance() : nullptr)
    {
        Runtime = GameInstance->GetSubsystem<UGahyeonRuntimeSubsystem>();
    }
    WriteEvidence(false);
}

void UGahyeonLiveSpeechCaptureComponent::TickComponent(
    float DeltaTime,
    ELevelTick TickType,
    FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
    if (!bEnabled || Runtime == nullptr) return;

    if (!bRequested)
    {
        const FGahyeonRuntimeFrameSnapshot Snapshot = Runtime->GetSnapshot();
        const bool bStrongViseme = Snapshot.bBackendConnected
            && Snapshot.ConversationPhase == TEXT("speaking")
            && !Snapshot.PrimaryViseme.IsEmpty()
            && Snapshot.PrimaryVisemeWeight >= 0.7;
        const bool bStrongAmplitudeJaw = Snapshot.bBackendConnected
            && Snapshot.ConversationPhase == TEXT("speaking")
            && Snapshot.bLipSyncActive
            && Snapshot.PrimaryViseme.IsEmpty()
            && Snapshot.JawOpen >= 0.25;
        const double Now = GetWorld() != nullptr ? GetWorld()->GetTimeSeconds() : 0.0;
        if (!bStrongViseme && !bStrongAmplitudeJaw)
        {
            StrongVisemeSinceSeconds = -1.0;
            return;
        }
        if (StrongVisemeSinceSeconds < 0.0)
        {
            StrongVisemeSinceSeconds = Now;
            return;
        }
        if (Now - StrongVisemeSinceSeconds >= 0.04)
        {
            CapturedViseme = bStrongViseme
                ? Snapshot.PrimaryViseme
                : TEXT("amplitude-jaw");
            CapturedWeight = bStrongViseme
                ? Snapshot.PrimaryVisemeWeight
                : Snapshot.JawOpen;
            CapturedGeneration = Snapshot.CurrentGeneration;
            if (UWorld* World = GetWorld())
            {
                for (TActorIterator<AGahyeonCharacterPawn> It(World); It; ++It)
                {
                    if (const UGahyeonMetaHumanFacialDriverComponent* FaceDriver =
                        It->FindComponentByClass<UGahyeonMetaHumanFacialDriverComponent>())
                    {
                        bCapturedFaceRigReady = FaceDriver->IsFaceRigReady();
                        CapturedAppliedJawOpen = FaceDriver->GetAppliedJawOpen();
                        break;
                    }
                }
            }
            FScreenshotRequest::RequestScreenshot(ScreenshotPath, false, false);
            bRequested = true;
            UE_LOG(LogTemp, Display,
                TEXT("Gahyeon live speech screenshot requested: viseme=%s weight=%.3f path=%s"),
                *CapturedViseme, CapturedWeight, *ScreenshotPath);
        }
        return;
    }

    if (!bFinalEvidenceWritten && IFileManager::Get().FileExists(*ScreenshotPath))
    {
        WriteEvidence(true);
        bFinalEvidenceWritten = true;
        SetComponentTickEnabled(false);
        UE_LOG(LogTemp, Display, TEXT("Gahyeon live speech visual evidence complete: %s"),
            *EvidencePath);
    }
}

void UGahyeonLiveSpeechCaptureComponent::WriteEvidence(bool bScreenshotPresent)
{
    FString VisualActorClass;
    if (UWorld* World = GetWorld())
    {
        for (TActorIterator<AGahyeonCharacterPawn> It(World); It; ++It)
        {
            if (AActor* Visual = It->GetVisualActor())
            {
                VisualActorClass = Visual->GetClass()->GetPathName();
                break;
            }
        }
    }
    TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
    Root->SetNumberField(TEXT("schemaVersion"), 1);
    Root->SetStringField(TEXT("iteration"), TEXT("v107"));
    Root->SetStringField(TEXT("status"),
        bScreenshotPresent ? TEXT("rendered-viseme-captured") : TEXT("waiting-for-viseme"));
    Root->SetBoolField(TEXT("screenshotPresent"), bScreenshotPresent);
    Root->SetStringField(TEXT("screenshot"), ScreenshotPath);
    Root->SetStringField(TEXT("visualActorClass"), VisualActorClass);
    Root->SetNumberField(TEXT("generation"), static_cast<double>(CapturedGeneration));
    Root->SetStringField(TEXT("primaryViseme"), CapturedViseme);
    Root->SetNumberField(TEXT("primaryVisemeWeight"), CapturedWeight);
    Root->SetStringField(TEXT("lipSyncSource"),
        CapturedViseme == TEXT("amplitude-jaw") ? TEXT("pcm-amplitude") : TEXT("viseme-timeline"));
    Root->SetBoolField(TEXT("metaHumanFaceRigReady"), bCapturedFaceRigReady);
    Root->SetNumberField(TEXT("appliedJawOpen"), CapturedAppliedJawOpen);
    Root->SetBoolField(TEXT("productionRuntimeConsumer"), true);
    Root->SetBoolField(TEXT("systemScreenCapture"), false);
    FString Json;
    const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Json);
    FJsonSerializer::Serialize(Root, Writer);
    FFileHelper::SaveStringToFile(Json + LINE_TERMINATOR, *EvidencePath);
}
