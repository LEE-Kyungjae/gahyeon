#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "IWebSocket.h"
#include "GahyeonTransportSubsystem.generated.h"

class UGahyeonRuntimePersistenceSubsystem;
class UGahyeonRuntimeSubsystem;

enum class EGahyeonTransportCallbackDisposition : uint8
{
    Current,
    OldConnection,
    ReplacedRuntime,
};

enum class EGahyeonConnectionBootstrap : uint8
{
    RestorePersistentState,
    ReuseLiveRuntime,
};

/** WebSocket lifecycle only; protocol state remains owned by RuntimeCore/runtime subsystem. */
UCLASS()
class GAHYEONSTAGE_API UGahyeonTransportSubsystem final : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    UFUNCTION(BlueprintCallable, Category = "Gahyeon|Network")
    void Configure(
        const FString& InEndpoint,
        const FString& InSessionId,
        const FString& InWorldId,
        const FString& InInstallationId,
        const FString& InDisplayName,
        const FString& InBearerToken);

    /** Selects the persona rendered by this connection before Connect(). */
    UFUNCTION(BlueprintCallable, Category = "Gahyeon|Network")
    bool SetCharacterId(const FString& InCharacterId);

    UFUNCTION(BlueprintCallable, Category = "Gahyeon|Network")
    bool Connect();

    UFUNCTION(BlueprintCallable, Category = "Gahyeon|Network")
    void Disconnect();

    UFUNCTION(BlueprintPure, Category = "Gahyeon|Network")
    bool IsSocketConnected() const;

    /** Last measured application-level heartbeat RTT, or -1 before the first pong. */
    UFUNCTION(BlueprintPure, Category = "Gahyeon|Network")
    double GetLastHeartbeatRttMillis() const { return LastHeartbeatRttMillis; }

    UFUNCTION(BlueprintPure, Category = "Gahyeon|Network")
    bool IsHeartbeatAwaitingPong() const { return !PendingHeartbeatCorrelationId.IsEmpty(); }

    UFUNCTION(BlueprintPure, Category = "Gahyeon|Network")
    int64 GetAcceptedHeartbeatPongCount() const { return AcceptedHeartbeatPongCount; }

    UFUNCTION(BlueprintPure, Category = "Gahyeon|Network")
    int64 GetHeartbeatTimeoutCount() const { return HeartbeatTimeoutCount; }

    UFUNCTION(BlueprintPure, Category = "Gahyeon|Network")
    int64 GetInvalidHeartbeatPongCount() const { return InvalidHeartbeatPongCount; }

    UFUNCTION(BlueprintPure, Category = "Gahyeon|Network")
    int64 GetStaleHeartbeatPongCount() const { return StaleHeartbeatPongCount; }

    /** Game-thread egress port used only after RuntimeCore persistence confirmation. */
    bool SendProtocolJson(const FString& Json);
    void RequestProtocolReconnect();
    FString GetHttpOrigin() const;
    const FString& GetBearerToken() const { return BearerToken; }
    const FString& GetSessionId() const { return SessionId; }
    FString GetStreamingSttEndpoint() const;

    /** Pure admission rule shared by socket callbacks and automation tests. */
    static EGahyeonTransportCallbackDisposition ClassifyCallback(
        uint64 CapturedConnectionGeneration,
        uint64 CapturedRuntimeEpoch,
        uint64 CurrentConnectionGeneration,
        uint64 CurrentRuntimeEpoch);

    /** Returns a safe server-advertised heartbeat interval, or INDEX_NONE when invalid. */
    static int32 NormalizeHeartbeatIntervalMillis(double IntervalMillis);

    /** Pure correlation rule used before a pong may update transport health. */
    static bool IsExpectedHeartbeatPong(
        const FString& PendingCorrelationId,
        const FString& ReceivedCorrelationId);

    /** Persistence is a GameInstance bootstrap, never a socket reconnect step. */
    static EGahyeonConnectionBootstrap SelectConnectionBootstrap(
        bool bPersistentStateRestored);

private:
    void OpenSocket(uint64 Generation, uint64 RuntimeEpoch, int64 LastSequence);
    void SendHello(uint64 Generation, uint64 RuntimeEpoch, int64 LastSequence);
    void HandleDisconnected(uint64 Generation);
    void ScheduleReconnect();
    void CancelReconnect();
    void StartHeartbeat(uint64 Generation, double IntervalSeconds);
    void StopHeartbeat();
    bool ApplyWelcomeHeartbeat(uint64 Generation, const FString& PayloadJson);
    bool ConsumeHeartbeatPong(
        uint64 Generation,
        const FString& CorrelationId,
        const FString& Delivery,
        const FString& PayloadJson);
    FString BuildHello(int64 LastSequence) const;
    FString BuildPing();

    UPROPERTY(Transient)
    TObjectPtr<UGahyeonRuntimeSubsystem> Runtime;

    UPROPERTY(Transient)
    TObjectPtr<UGahyeonRuntimePersistenceSubsystem> Persistence;

    TSharedPtr<IWebSocket> Socket;
    FString Endpoint;
    FString SessionId;
    FString WorldId;
    FString InstallationId;
    FString DisplayName;
    FString CharacterId = TEXT("gahyeon");
    FString BearerToken;
    bool bConnectPending = false;
    bool bShouldReconnect = false;
    // A socket reconnect must not replace the live RuntimeCore. Persistence is
    // restored once for this GameInstance; later loads only supply the latest
    // durable replay cursor used by the new hello.
    bool bPersistentStateRestored = false;
    int32 ReconnectAttempt = 0;
    FTSTicker::FDelegateHandle ReconnectTickerHandle;
    FTSTicker::FDelegateHandle HeartbeatTickerHandle;
    uint64 ConnectionGeneration = 0;
    FString PendingHeartbeatCorrelationId;
    double PendingHeartbeatSentAtSeconds = 0.0;
    double LastHeartbeatRttMillis = -1.0;
    int64 AcceptedHeartbeatPongCount = 0;
    int64 HeartbeatTimeoutCount = 0;
    int64 InvalidHeartbeatPongCount = 0;
    int64 StaleHeartbeatPongCount = 0;
};
