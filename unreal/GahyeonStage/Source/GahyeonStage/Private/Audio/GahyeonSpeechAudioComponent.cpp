#include "Audio/GahyeonSpeechAudioComponent.h"

#include "Components/AudioComponent.h"
#include "Engine/GameInstance.h"
#include "Http.h"
#include "HttpModule.h"
#include "HAL/PlatformTime.h"
#include "HAL/CriticalSection.h"
#include "Interfaces/IHttpResponse.h"
#include "Containers/Queue.h"
#include "Network/GahyeonTransportSubsystem.h"
#include "Sound/SoundWaveProcedural.h"

namespace
{
uint16 ReadU16(const uint8* Data)
{
    return static_cast<uint16>(Data[0])
        | static_cast<uint16>(static_cast<uint16>(Data[1]) << 8);
}
}

struct UGahyeonSpeechAudioComponent::FStreamIngress
{
    void Status(int32 InStatus)
    {
        FScopeLock Lock(&Mutex);
        StatusCode = InStatus;
    }

    void Header(const FString& Name, const FString& Value)
    {
        FScopeLock Lock(&Mutex);
        Headers.Add(Name.ToLower(), Value.TrimStartAndEnd().ToLower());
    }

    bool Offer(const void* Data, int64 Bytes)
    {
        if (Data == nullptr || Bytes <= 0 || Bytes > MaxAudioBytes) return false;
        FScopeLock Lock(&Mutex);
        if (bCancelled || bFailed || TotalBytes > MaxAudioBytes - Bytes) return false;
        TArray<uint8> Chunk;
        Chunk.Append(static_cast<const uint8*>(Data), static_cast<int32>(Bytes));
        Chunks.Enqueue(MoveTemp(Chunk));
        TotalBytes += Bytes;
        if (TotalBytes >= NextLogBytes)
        {
            UE_LOG(LogTemp, Display, TEXT("Gahyeon PCM HTTP received bytes=%lld"), TotalBytes);
            NextLogBytes += 64 * 1024;
        }
        return true;
    }

    void Finish(bool bSucceeded)
    {
        FScopeLock Lock(&Mutex);
        bCompleted = bSucceeded && StatusCode == 200 && TotalBytes > 0;
        bFailed = !bCompleted;
        UE_LOG(LogTemp, Display,
            TEXT("Gahyeon PCM HTTP finished success=%s status=%d bytes=%lld"),
            bCompleted ? TEXT("true") : TEXT("false"), StatusCode, TotalBytes);
    }

    void Cancel()
    {
        FScopeLock Lock(&Mutex);
        bCancelled = true;
        UE_LOG(LogTemp, Display, TEXT("Gahyeon PCM HTTP cancelled bytes=%lld"), TotalBytes);
    }

    bool Drain(TArray<uint8>& Out)
    {
        TArray<uint8> Chunk;
        bool bAny = false;
        while (Chunks.Dequeue(Chunk))
        {
            Out.Append(Chunk);
            bAny = true;
        }
        return bAny;
    }

    void Snapshot(bool& bOutFormatReady, bool& bOutComplete, bool& bOutFailed, int64& OutBytes)
    {
        FScopeLock Lock(&Mutex);
        const FString* ContentType = Headers.Find(TEXT("content-type"));
        const FString* SampleRate = Headers.Find(TEXT("x-sample-rate"));
        const FString* SampleFormat = Headers.Find(TEXT("x-sample-format"));
        const FString* Channels = Headers.Find(TEXT("x-channels"));
        bOutFormatReady = StatusCode == 200 && ContentType != nullptr
            && ContentType->StartsWith(TEXT("audio/pcm"))
            && SampleRate != nullptr && *SampleRate == TEXT("24000")
            && SampleFormat != nullptr && *SampleFormat == TEXT("s16le")
            && Channels != nullptr && *Channels == TEXT("1");
        bOutComplete = bCompleted;
        bOutFailed = bFailed || bCancelled;
        OutBytes = TotalBytes;
    }

    FCriticalSection Mutex;
    TQueue<TArray<uint8>, EQueueMode::Mpsc> Chunks;
    TMap<FString, FString> Headers;
    int64 TotalBytes = 0;
    int64 NextLogBytes = 64 * 1024;
    int32 StatusCode = 0;
    bool bCompleted = false;
    bool bFailed = false;
    bool bCancelled = false;
};

namespace
{
uint32 ReadU32(const uint8* Data)
{
    return static_cast<uint32>(Data[0])
        | (static_cast<uint32>(Data[1]) << 8)
        | (static_cast<uint32>(Data[2]) << 16)
        | (static_cast<uint32>(Data[3]) << 24);
}

bool FourCc(const uint8* Data, const char A, const char B, const char C, const char D)
{
    return Data[0] == static_cast<uint8>(A) && Data[1] == static_cast<uint8>(B)
        && Data[2] == static_cast<uint8>(C) && Data[3] == static_cast<uint8>(D);
}
}

UGahyeonSpeechAudioComponent::UGahyeonSpeechAudioComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.bStartWithTickEnabled = true;
}

void UGahyeonSpeechAudioComponent::BeginPlay()
{
    Super::BeginPlay();
    if (UGameInstance* GameInstance = GetWorld() != nullptr
        ? GetWorld()->GetGameInstance() : nullptr)
    {
        Runtime = GameInstance->GetSubsystem<UGahyeonRuntimeSubsystem>();
    }
    if (Runtime != nullptr)
    {
        ObservedRuntimeEpoch = Runtime->GetRuntimeEpoch();
        Runtime->OnAudioInterruptRequested.AddDynamic(
            this, &UGahyeonSpeechAudioComponent::HandleInterruptRequested);
    }
    if (HttpBaseUrl.IsEmpty())
    {
        RefreshTransportConfiguration();
    }
    AudioComponent = NewObject<UAudioComponent>(GetOwner(), TEXT("GahyeonSpeechAudio"));
    if (AudioComponent != nullptr)
    {
        AudioComponent->bAutoActivate = false;
        AudioComponent->bIsUISound = true;
        AudioComponent->OnAudioFinished.AddDynamic(
            this, &UGahyeonSpeechAudioComponent::HandleAudioFinished);
        AudioComponent->OnAudioSingleEnvelopeValue.AddDynamic(
            this, &UGahyeonSpeechAudioComponent::HandleEnvelopeValue);
        AudioComponent->RegisterComponent();
    }
}

void UGahyeonSpeechAudioComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    UE_LOG(LogTemp, Display, TEXT("Gahyeon speech device EndPlay reason=%d"),
        static_cast<int32>(EndPlayReason));
    ++RequestSerial;
    if (ActiveRequest.IsValid()) ActiveRequest->CancelRequest();
    ActiveRequest.Reset();
    if (Runtime != nullptr)
    {
        Runtime->OnAudioInterruptRequested.RemoveDynamic(
            this, &UGahyeonSpeechAudioComponent::HandleInterruptRequested);
    }
    if (AudioComponent != nullptr)
    {
        AudioComponent->OnAudioFinished.RemoveDynamic(
            this, &UGahyeonSpeechAudioComponent::HandleAudioFinished);
        AudioComponent->OnAudioSingleEnvelopeValue.RemoveDynamic(
            this, &UGahyeonSpeechAudioComponent::HandleEnvelopeValue);
    }
    FailReservedSegment();
    ClearDeviceState(true);
    Runtime = nullptr;
    Super::EndPlay(EndPlayReason);
}

void UGahyeonSpeechAudioComponent::TickComponent(
    float DeltaTime,
    ELevelTick TickType,
    FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
    if (Runtime != nullptr && Runtime->GetRuntimeEpoch() != ObservedRuntimeEpoch)
    {
        // RuntimeCore replacement revokes every reservation owned by the old
        // coordinator. Serial invalidation also makes a late HTTP callback inert.
        UE_LOG(LogTemp, Display,
            TEXT("Gahyeon speech device runtime epoch changed old=%llu new=%llu"),
            ObservedRuntimeEpoch, Runtime->GetRuntimeEpoch());
        ClearDeviceState(true);
        ObservedRuntimeEpoch = Runtime->GetRuntimeEpoch();
    }
    if (bPlaybackReported && PlaybackDeadlineSeconds > 0.0
        && FPlatformTime::Seconds() >= PlaybackDeadlineSeconds)
    {
        // Some procedural sources do not emit a finish delegate when their FIFO
        // drains. The PCM-derived duration plus margin prevents queue deadlock.
        AudioComponent->Stop();
        if (bHasReservedSegment) HandleAudioFinished();
    }
    if (bPlaybackReported && Runtime != nullptr)
    {
        const int64 PositionMs = static_cast<int64>(FMath::Max(
            0.0, FPlatformTime::Seconds() - PlaybackStartedSeconds) * 1000.0);
        Runtime->UpdateSpeechPlaybackSample(PositionMs, CurrentEnvelopeAmplitude);
    }
    DrainPcmStream();
    TryAcquireNext();
}

void UGahyeonSpeechAudioComponent::Configure(
    const FString& InHttpBaseUrl,
    const FString& InBearerToken)
{
    HttpBaseUrl = InHttpBaseUrl.TrimStartAndEnd();
    while (HttpBaseUrl.EndsWith(TEXT("/"))) HttpBaseUrl.LeftChopInline(1);
    BearerToken = InBearerToken;
}

bool UGahyeonSpeechAudioComponent::IsSpeechActive() const
{
    return bHasReservedSegment || ActiveRequest.IsValid()
        || (AudioComponent != nullptr && AudioComponent->IsPlaying());
}

void UGahyeonSpeechAudioComponent::TryAcquireNext()
{
    if (Runtime == nullptr || AudioComponent == nullptr || bHasReservedSegment
        || ActiveRequest.IsValid() || AudioComponent->IsPlaying())
    {
        return;
    }
    FGahyeonPreparedSpeechSegment Segment;
    if (!Runtime->AcquireNextSpeechSegment(Segment)) return;
    ReservedSegment = MoveTemp(Segment);
    bHasReservedSegment = true;
    bPlaybackReported = false;
    StartDownload(ReservedSegment);
}

void UGahyeonSpeechAudioComponent::RefreshTransportConfiguration()
{
    if (UGameInstance* GameInstance = GetWorld() != nullptr
        ? GetWorld()->GetGameInstance() : nullptr)
    {
        if (const UGahyeonTransportSubsystem* Transport =
            GameInstance->GetSubsystem<UGahyeonTransportSubsystem>())
        {
            Configure(Transport->GetHttpOrigin(), Transport->GetBearerToken());
        }
    }
}

void UGahyeonSpeechAudioComponent::StartDownload(
    const FGahyeonPreparedSpeechSegment& Segment)
{
    if (HttpBaseUrl.IsEmpty()) RefreshTransportConfiguration();
    bStreamingPcm = Segment.MimeType.Equals(TEXT("audio/pcm"), ESearchCase::IgnoreCase);
    if (!bStreamingPcm
        && !Segment.MimeType.Equals(TEXT("audio/wav"), ESearchCase::IgnoreCase)
        && !Segment.MimeType.Equals(TEXT("audio/x-wav"), ESearchCase::IgnoreCase))
    {
        FailReservedSegment();
        return;
    }
    const FString Url = ResolveAudioUrl(Segment.AudioUrl);
    if (Url.IsEmpty())
    {
        FailReservedSegment();
        return;
    }
    const uint64 Serial = ++RequestSerial;
    ActiveRequest = FHttpModule::Get().CreateRequest();
    ActiveRequest->SetURL(Url);
    ActiveRequest->SetVerb(TEXT("GET"));
    ActiveRequest->SetHeader(TEXT("Accept"), bStreamingPcm ? TEXT("audio/pcm") : TEXT("audio/wav"));
    ActiveRequest->SetTimeout(FMath::Clamp(AudioDownloadTimeoutSeconds, 1.0f, 30.0f));
    if (!BearerToken.IsEmpty())
    {
        ActiveRequest->SetHeader(TEXT("Authorization"), TEXT("Bearer ") + BearerToken);
    }
    if (bStreamingPcm)
    {
        StreamIngress = MakeShared<FStreamIngress, ESPMode::ThreadSafe>();
        const TSharedPtr<FStreamIngress, ESPMode::ThreadSafe> Ingress = StreamIngress;
        ActiveRequest->OnStatusCodeReceived().BindLambda(
            [Ingress](FHttpRequestPtr, int32 StatusCode) { Ingress->Status(StatusCode); });
        ActiveRequest->OnHeaderReceived().BindLambda(
            [Ingress](FHttpRequestPtr, const FString& Name, const FString& Value)
            { Ingress->Header(Name, Value); });
        const bool bStreamBound = ActiveRequest->SetResponseBodyReceiveStreamDelegateV2(
            FHttpRequestStreamDelegateV2::CreateLambda(
                [Ingress](void* Data, int64& Bytes)
                {
                    if (!Ingress->Offer(Data, Bytes)) Bytes = 0;
                }));
        if (!bStreamBound)
        {
            ActiveRequest.Reset();
            StreamIngress.Reset();
            FailReservedSegment();
            return;
        }
    }
    ActiveRequest->OnProcessRequestComplete().BindUObject(
        this, &UGahyeonSpeechAudioComponent::HandleDownload, Serial);
    if (!ActiveRequest->ProcessRequest())
    {
        ActiveRequest.Reset();
        FailReservedSegment();
    }
}

void UGahyeonSpeechAudioComponent::HandleDownload(
    FHttpRequestPtr Request,
    FHttpResponsePtr Response,
    bool bSucceeded,
    uint64 Serial)
{
    (void)Request;
    if (Serial != RequestSerial || !bHasReservedSegment) return;
    ActiveRequest.Reset();
    if (bStreamingPcm)
    {
        if (StreamIngress.IsValid())
        {
            StreamIngress->Finish(bSucceeded && Response.IsValid()
                && EHttpResponseCodes::IsOk(Response->GetResponseCode()));
        }
        return;
    }
    const int32 ContentBytes = Response.IsValid() ? Response->GetContent().Num() : 0;
    if (!bSucceeded || !Response.IsValid()
        || !EHttpResponseCodes::IsOk(Response->GetResponseCode())
        || ContentBytes <= 0 || ContentBytes > MaxAudioBytes
        || !StartPcmPlayback(Response->GetContent()))
    {
        FailReservedSegment();
    }
}

void UGahyeonSpeechAudioComponent::DrainPcmStream()
{
    if (!bStreamingPcm || !StreamIngress.IsValid() || !bHasReservedSegment) return;
    bool bFormatReady = false;
    bool bComplete = false;
    bool bFailed = false;
    int64 TotalBytes = 0;
    StreamIngress->Drain(StreamPendingPcm);
    StreamIngress->Snapshot(bFormatReady, bComplete, bFailed, TotalBytes);
    if (bFailed || (bComplete && !bFormatReady)
        || StreamPendingPcm.Num() > MaxAudioBytes)
    {
        FailReservedSegment();
        return;
    }
    const int32 FrameBytes = sizeof(int16);
    const int32 ReadyBytes = StreamPendingPcm.Num() - (StreamPendingPcm.Num() % FrameBytes);
    if (!bFormatReady || ReadyBytes <= 0) return;
    if (ActiveWave == nullptr)
    {
        if (ReadyBytes < StreamPrebufferBytes && !bComplete) return;
        ActiveWave = NewObject<USoundWaveProcedural>(this);
        if (ActiveWave == nullptr)
        {
            FailReservedSegment();
            return;
        }
        ActiveWave->NumChannels = 1;
        ActiveWave->SetSampleRate(24000);
        ActiveWave->Duration = INDEFINITELY_LOOPING_DURATION;
        ActiveWave->SoundGroup = SOUNDGROUP_Voice;
        ActiveWave->bLooping = false;
        ActiveWave->QueueAudio(StreamPendingPcm.GetData(), ReadyBytes);
        StreamPendingPcm.RemoveAt(0, ReadyBytes, EAllowShrinking::No);
        AudioComponent->SetSound(ActiveWave);
        AudioComponent->Play();
        if (!AudioComponent->IsPlaying() || Runtime == nullptr
            || !Runtime->NotifySpeechPlaybackStarted(ReservedSegment.UtteranceId))
        {
            FailReservedSegment();
            return;
        }
        bPlaybackReported = true;
        PlaybackStartedSeconds = FPlatformTime::Seconds();
    }
    else
    {
        ActiveWave->QueueAudio(StreamPendingPcm.GetData(), ReadyBytes);
        StreamPendingPcm.RemoveAt(0, ReadyBytes, EAllowShrinking::No);
        if (bPlaybackReported && AudioComponent != nullptr
            && !AudioComponent->IsPlaying())
        {
            // Procedural sources may report an underflow as finished before
            // the HTTP producer closes. Keep the RuntimeCore reservation and
            // resume from the next bounded chunk instead of truncating speech.
            AudioComponent->Play();
        }
    }
    if (bComplete && StreamPendingPcm.IsEmpty() && TotalBytes > 0 && bPlaybackReported)
    {
        const double DurationSeconds = static_cast<double>(TotalBytes) / (24000.0 * sizeof(int16));
        PlaybackDeadlineSeconds = PlaybackStartedSeconds + DurationSeconds + 0.5;
        StreamIngress.Reset();
    }
}

bool UGahyeonSpeechAudioComponent::StartPcmPlayback(const TArray<uint8>& Bytes)
{
    FWavPcmView View;
    if (AudioComponent == nullptr || !ParsePcm16Wav(Bytes, View)) return false;
    ActiveWave = NewObject<USoundWaveProcedural>(this);
    if (ActiveWave == nullptr) return false;
    ActiveWave->NumChannels = View.Channels;
    ActiveWave->SetSampleRate(View.SampleRate);
    ActiveWave->Duration = static_cast<float>(View.PcmBytes)
        / static_cast<float>(View.Channels * sizeof(int16) * View.SampleRate);
    ActiveWave->SoundGroup = SOUNDGROUP_Voice;
    ActiveWave->bLooping = false;
    ActiveWave->QueueAudio(View.PcmData, View.PcmBytes);
    AudioComponent->SetSound(ActiveWave);
    AudioComponent->Play();
    if (!AudioComponent->IsPlaying()
        || Runtime == nullptr
        || !Runtime->NotifySpeechPlaybackStarted(ReservedSegment.UtteranceId))
    {
        AudioComponent->Stop();
        ActiveWave = nullptr;
        return false;
    }
    bPlaybackReported = true;
    PlaybackStartedSeconds = FPlatformTime::Seconds();
    PlaybackDeadlineSeconds = FPlatformTime::Seconds()
        + static_cast<double>(ActiveWave->Duration) + 0.5;
    return true;
}

void UGahyeonSpeechAudioComponent::FailReservedSegment()
{
    UE_LOG(LogTemp, Display, TEXT("Gahyeon speech segment failed utterance=%s streaming=%s"),
        *ReservedSegment.UtteranceId, bStreamingPcm ? TEXT("true") : TEXT("false"));
    if (bHasReservedSegment && Runtime != nullptr)
    {
        Runtime->NotifySpeechPlaybackFailed(ReservedSegment.UtteranceId);
    }
    ClearDeviceState(false);
}

void UGahyeonSpeechAudioComponent::ClearDeviceState(bool bStopAudio)
{
    ++RequestSerial;
    if (ActiveRequest.IsValid()) ActiveRequest->CancelRequest();
    ActiveRequest.Reset();
    if (StreamIngress.IsValid()) StreamIngress->Cancel();
    StreamIngress.Reset();
    StreamPendingPcm.Reset();
    bStreamingPcm = false;
    bHasReservedSegment = false;
    bPlaybackReported = false;
    PlaybackDeadlineSeconds = 0.0;
    PlaybackStartedSeconds = 0.0;
    CurrentEnvelopeAmplitude = 0.0;
    ReservedSegment = {};
    if (bStopAudio && AudioComponent != nullptr) AudioComponent->Stop();
    ActiveWave = nullptr;
}

FString UGahyeonSpeechAudioComponent::ResolveAudioUrl(const FString& AudioUrl) const
{
    const FString Trimmed = AudioUrl.TrimStartAndEnd();
    if (Trimmed.StartsWith(TEXT("https://")) || Trimmed.StartsWith(TEXT("http://")))
    {
        return Trimmed;
    }
    if (!Trimmed.StartsWith(TEXT("/")) || HttpBaseUrl.IsEmpty()) return {};
    return HttpBaseUrl + Trimmed;
}

bool UGahyeonSpeechAudioComponent::ParsePcm16Wav(
    const TArray<uint8>& Bytes,
    FWavPcmView& Out)
{
    Out = {};
    if (Bytes.Num() < 44 || !FourCc(Bytes.GetData(), 'R', 'I', 'F', 'F')
        || !FourCc(Bytes.GetData() + 8, 'W', 'A', 'V', 'E'))
    {
        return false;
    }
    uint16 Format = 0;
    uint16 Channels = 0;
    uint32 SampleRate = 0;
    uint16 BitsPerSample = 0;
    const uint8* PcmData = nullptr;
    uint32 PcmBytes = 0;
    int64 Offset = 12;
    while (Offset + 8 <= Bytes.Num())
    {
        const uint8* Chunk = Bytes.GetData() + Offset;
        const uint32 ChunkBytes = ReadU32(Chunk + 4);
        const int64 DataStart = Offset + 8;
        if (ChunkBytes > static_cast<uint32>(Bytes.Num())
            || DataStart + static_cast<int64>(ChunkBytes) > Bytes.Num())
        {
            return false;
        }
        if (FourCc(Chunk, 'f', 'm', 't', ' ') && ChunkBytes >= 16)
        {
            Format = ReadU16(Bytes.GetData() + DataStart);
            Channels = ReadU16(Bytes.GetData() + DataStart + 2);
            SampleRate = ReadU32(Bytes.GetData() + DataStart + 4);
            BitsPerSample = ReadU16(Bytes.GetData() + DataStart + 14);
        }
        else if (FourCc(Chunk, 'd', 'a', 't', 'a'))
        {
            PcmData = Bytes.GetData() + DataStart;
            PcmBytes = ChunkBytes;
        }
        Offset = DataStart + ChunkBytes + (ChunkBytes & 1U);
    }
    if (Format != 1 || (Channels != 1 && Channels != 2)
        || SampleRate < 8000 || SampleRate > 192000 || BitsPerSample != 16
        || PcmData == nullptr || PcmBytes == 0 || PcmBytes > MaxAudioBytes
        || PcmBytes % (Channels * sizeof(int16)) != 0)
    {
        return false;
    }
    Out.SampleRate = static_cast<int32>(SampleRate);
    Out.Channels = static_cast<int32>(Channels);
    Out.PcmData = PcmData;
    Out.PcmBytes = static_cast<int32>(PcmBytes);
    return true;
}

void UGahyeonSpeechAudioComponent::HandleAudioFinished()
{
    if (!bHasReservedSegment) return;
    if (bStreamingPcm && StreamIngress.IsValid())
    {
        // This is an underflow boundary, not utterance completion. The HTTP
        // request still owns future PCM and DrainPcmStream will resume it.
        UE_LOG(LogTemp, Display, TEXT("Gahyeon PCM procedural underflow; awaiting HTTP"));
        return;
    }
    const FString UtteranceId = ReservedSegment.UtteranceId;
    const bool bWasReported = bPlaybackReported;
    ClearDeviceState(false);
    if (bWasReported && Runtime != nullptr)
    {
        Runtime->NotifySpeechPlaybackFinished(UtteranceId);
    }
}

void UGahyeonSpeechAudioComponent::HandleEnvelopeValue(
    const USoundWave* PlayingSoundWave,
    float EnvelopeValue)
{
    if (bPlaybackReported && PlayingSoundWave == ActiveWave.Get()
        && FMath::IsFinite(EnvelopeValue))
    {
        CurrentEnvelopeAmplitude = FMath::Clamp(
            static_cast<double>(EnvelopeValue), 0.0, 1.0);
    }
}

void UGahyeonSpeechAudioComponent::HandleInterruptRequested(const FString& UtteranceId)
{
    if (!bHasReservedSegment || ReservedSegment.UtteranceId != UtteranceId) return;
    UE_LOG(LogTemp, Display, TEXT("Gahyeon speech interrupt requested utterance=%s"),
        *UtteranceId);
    // RuntimeCore has already revoked this ownership. Clear our identity before
    // Stop(), so a synchronous OnAudioFinished cannot report a false completion.
    ClearDeviceState(true);
    if (Runtime != nullptr) Runtime->NotifyInterruptedAudioStopped();
}
