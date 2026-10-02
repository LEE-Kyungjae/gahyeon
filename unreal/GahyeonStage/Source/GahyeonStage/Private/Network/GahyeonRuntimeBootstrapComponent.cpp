#include "Network/GahyeonRuntimeBootstrapComponent.h"

#include "Engine/GameInstance.h"
#include "HAL/PlatformMisc.h"
#include "HAL/PlatformProcess.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Network/GahyeonTransportSubsystem.h"

UGahyeonRuntimeBootstrapComponent::UGahyeonRuntimeBootstrapComponent()
{
    PrimaryComponentTick.bCanEverTick = false;
}

void UGahyeonRuntimeBootstrapComponent::BeginPlay()
{
    Super::BeginPlay();
    if (!FParse::Param(FCommandLine::Get(), TEXT("GahyeonAutoConnect"))) return;

    FString Endpoint;
    FString SessionId;
    FString WorldId;
    FString InstallationId;
    FString DisplayName = TEXT("Gahyeon Desktop");
    FString CharacterId = TEXT("gahyeon");
    const bool bConfigured =
        FParse::Value(FCommandLine::Get(), TEXT("GahyeonCoreEndpoint="), Endpoint)
        && FParse::Value(FCommandLine::Get(), TEXT("GahyeonSessionId="), SessionId)
        && FParse::Value(FCommandLine::Get(), TEXT("GahyeonWorldId="), WorldId)
        && FParse::Value(
            FCommandLine::Get(), TEXT("GahyeonInstallationId="), InstallationId);
    FParse::Value(FCommandLine::Get(), TEXT("GahyeonDisplayName="), DisplayName);
    FParse::Value(FCommandLine::Get(), TEXT("GahyeonCharacterId="), CharacterId);
    if (!bConfigured)
    {
        UE_LOG(LogTemp, Error, TEXT("Gahyeon auto-connect rejected: required identity argument missing"));
        return;
    }

    UGameInstance* GameInstance = GetWorld() != nullptr
        ? GetWorld()->GetGameInstance() : nullptr;
    UGahyeonTransportSubsystem* Transport = GameInstance != nullptr
        ? GameInstance->GetSubsystem<UGahyeonTransportSubsystem>() : nullptr;
    if (Transport == nullptr)
    {
        UE_LOG(LogTemp, Error, TEXT("Gahyeon auto-connect rejected: transport unavailable"));
        return;
    }

    const FString BearerToken = FPlatformMisc::GetEnvironmentVariable(
        TEXT("GAHYEON_CLIENT_TOKEN"));
    Transport->Configure(
        Endpoint, SessionId, WorldId, InstallationId, DisplayName, BearerToken);
    if (!Transport->SetCharacterId(CharacterId))
    {
        UE_LOG(LogTemp, Error, TEXT("Gahyeon auto-connect rejected: invalid character id"));
        return;
    }
    if (!Transport->Connect())
    {
        UE_LOG(LogTemp, Error, TEXT("Gahyeon auto-connect failed to start"));
        return;
    }
    UE_LOG(LogTemp, Display, TEXT("Gahyeon auto-connect started for %s"), *Endpoint);
}
