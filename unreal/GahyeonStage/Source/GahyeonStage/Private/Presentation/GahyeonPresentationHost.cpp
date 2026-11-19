#include "Presentation/GahyeonPresentationHost.h"

#include "Audio/GahyeonSpeechAudioComponent.h"
#include "Components/SceneComponent.h"
#include "Debug/GahyeonLookingGlassBenchmarkComponent.h"
#include "Debug/GahyeonRealtimeBenchmarkComponent.h"
#include "Debug/GahyeonLiveSpeechCaptureComponent.h"
#include "Network/GahyeonRuntimeBootstrapComponent.h"

AGahyeonPresentationHost::AGahyeonPresentationHost()
{
    PrimaryActorTick.bCanEverTick = false;
    SetActorEnableCollision(false);
    SetCanBeDamaged(false);
    SetActorHiddenInGame(true);
    SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    RootComponent = SceneRoot;
    SpeechAudio = CreateDefaultSubobject<UGahyeonSpeechAudioComponent>(TEXT("SpeechAudio"));
    RuntimeBootstrap = CreateDefaultSubobject<UGahyeonRuntimeBootstrapComponent>(
        TEXT("RuntimeBootstrap"));
    LookingGlassBenchmark = CreateDefaultSubobject<UGahyeonLookingGlassBenchmarkComponent>(
        TEXT("LookingGlassBenchmark"));
    RealtimeBenchmark = CreateDefaultSubobject<UGahyeonRealtimeBenchmarkComponent>(
        TEXT("RealtimeBenchmark"));
    LiveSpeechCapture = CreateDefaultSubobject<UGahyeonLiveSpeechCaptureComponent>(
        TEXT("LiveSpeechCapture"));
}
