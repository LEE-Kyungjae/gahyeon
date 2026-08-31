#include "CoreMinimal.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "CineCameraComponent.h"
#include "Animation/SkeletalMeshActor.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "FrameGrabber.h"
#include "HAL/PlatformMemory.h"
#include "Modules/ModuleManager.h"
#include "Framework/Application/SlateApplication.h"
#include "Slate/SceneViewport.h"
#include "Widgets/SViewport.h"
#include "MacIOSurfaceBridge.h"
#include "Async/ParallelFor.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

namespace
{
constexpr uint32 FrameMagic = 0x47485247; // GHRG
constexpr uint32 FrameVersion = 1;
constexpr int32 FrameWidth = 1600;
constexpr int32 FrameHeight = 1258;
constexpr int32 FrameStride = FrameWidth * 4;
constexpr SIZE_T HeaderBytes = 64;
constexpr SIZE_T FrameBytes = SIZE_T(FrameStride) * FrameHeight;
constexpr SIZE_T RegionBytes = HeaderBytes + FrameBytes * 2;
constexpr uint32 ControlMagic = 0x47484354; // GHCT
constexpr SIZE_T ControlBytes = 64;

struct alignas(64) FSharedFrameHeader
{
    uint32 Magic = FrameMagic;
    uint32 Version = FrameVersion;
    uint32 Width = FrameWidth;
    uint32 Height = FrameHeight;
    uint32 Stride = FrameStride;
    volatile uint32 ActiveBuffer = 0;
    volatile uint64 Sequence = 0;
    uint32 AlphaMin = 255;
    uint32 AlphaMax = 255;
    uint32 BoundsMinX = 0;
    uint32 BoundsMinY = 0;
    uint32 BoundsMaxX = FrameWidth - 1;
    uint32 BoundsMaxY = FrameHeight - 1;
    uint32 ViewIndex = 0;
    uint32 ViewCount = 1;
};
static_assert(sizeof(FSharedFrameHeader) == HeaderBytes);

struct alignas(64) FSharedOverlayControl
{
    uint32 Magic = ControlMagic;
    uint32 Version = 1;
    volatile float YawDegrees = 0.0f;
    uint32 Reserved0 = 0;
    volatile uint64 Sequence = 0;
    volatile uint64 ResetSequence = 0;
    uint8 Reserved[32] = {};
};
static_assert(sizeof(FSharedOverlayControl) == ControlBytes);
}

class FGahyeonDesktopMetaHumanPOCModule final : public IModuleInterface
{
public:
    virtual void StartupModule() override
    {
#if PLATFORM_MAC
        StartGahyeonMacIOSurfaceBridge();
        const bool bEnableCPUFallback = FParse::Param(FCommandLine::Get(), TEXT("GahyeonCPUAlphaFallback"));
        bEnableLookingGlassQuilt = FParse::Param(
            FCommandLine::Get(), TEXT("GahyeonLookingGlassQuilt"));
        if (bEnableLookingGlassQuilt)
        {
            const FString ViewCountValue = FPlatformMisc::GetEnvironmentVariable(
                TEXT("GAHYEON_LOOKING_GLASS_VIEW_COUNT"));
            const FString ViewConeValue = FPlatformMisc::GetEnvironmentVariable(
                TEXT("GAHYEON_LOOKING_GLASS_VIEW_CONE"));
            if (!ViewCountValue.IsEmpty())
            {
                LookingGlassViewCount = FMath::Clamp(uint32(FCString::Atoi(*ViewCountValue)), 2u, 256u);
            }
            if (!ViewConeValue.IsEmpty())
            {
                LookingGlassViewConeDegrees = FMath::Clamp(FCString::Atof(*ViewConeValue), 1.0f, 180.0f);
            }
            TickHandle = FTSTicker::GetCoreTicker().AddTicker(
                FTickerDelegate::CreateRaw(this, &FGahyeonDesktopMetaHumanPOCModule::Tick));
        }
        if (!bEnableCPUFallback)
        {
            UE_LOG(LogTemp, Display, TEXT("Gahyeon GPU IOSurface bridge active; CPU fallback disabled"));
            return;
        }
        SharedRegion = FPlatformMemory::MapNamedSharedMemoryRegion(
            TEXT("gahyeon_rgba_v003"), true,
            FPlatformMemory::ESharedMemoryAccess::Read | FPlatformMemory::ESharedMemoryAccess::Write,
            RegionBytes);
        if (SharedRegion)
        {
            FMemory::Memzero(SharedRegion->GetAddress(), RegionBytes);
            new (SharedRegion->GetAddress()) FSharedFrameHeader();
            if (!TickHandle.IsValid())
            {
                TickHandle = FTSTicker::GetCoreTicker().AddTicker(
                    FTickerDelegate::CreateRaw(this, &FGahyeonDesktopMetaHumanPOCModule::Tick));
            }
        }
        ControlRegion = FPlatformMemory::MapNamedSharedMemoryRegion(
            TEXT("gahyeon_overlay_control_v001"), true,
            FPlatformMemory::ESharedMemoryAccess::Read | FPlatformMemory::ESharedMemoryAccess::Write,
            ControlBytes);
        if (ControlRegion)
        {
            FMemory::Memzero(ControlRegion->GetAddress(), ControlBytes);
            new (ControlRegion->GetAddress()) FSharedOverlayControl();
        }
        UE_LOG(LogTemp, Display, TEXT("Gahyeon CPU direct-alpha fallback explicitly enabled"));
#endif
    }

    virtual void ShutdownModule() override
    {
#if PLATFORM_MAC
        if (LookingGlassCamera.IsValid())
        {
            LookingGlassCamera->SetActorLocation(OriginalCameraLocation);
            LookingGlassCamera->SetActorRotation(OriginalCameraRotation);
            if (UCineCameraComponent* CineCamera = Cast<UCineCameraComponent>(
                    LookingGlassCamera->GetCameraComponent()))
            {
                CineCamera->Filmback.SensorHorizontalOffset = OriginalSensorHorizontalOffset;
            }
        }
        StopGahyeonMacIOSurfaceBridge();
        if (TickHandle.IsValid())
        {
            FTSTicker::GetCoreTicker().RemoveTicker(TickHandle);
        }
        if (FrameGrabber)
        {
            FrameGrabber->StopCapturingFrames();
            FrameGrabber->Shutdown();
            FrameGrabber.Reset();
        }
        if (SharedRegion)
        {
            FPlatformMemory::UnmapNamedSharedMemoryRegion(SharedRegion);
            SharedRegion = nullptr;
        }
        if (ControlRegion)
        {
            FPlatformMemory::UnmapNamedSharedMemoryRegion(ControlRegion);
            ControlRegion = nullptr;
        }
#endif
    }

private:
    bool Tick(float DeltaSeconds)
    {
#if PLATFORM_MAC
        ApplyOverlayControl();
        if (bEnableLookingGlassQuilt && !FrameGrabber)
        {
            const uint64 GPUSequence = GetGahyeonMacIOSurfaceSequence();
            if (!bGPUViewPrepared || GPUSequence != LastGPUSequence)
            {
                if (bGPUViewPrepared)
                {
                    CurrentViewIndex = (CurrentViewIndex + 1) % LookingGlassViewCount;
                }
                if (PrepareLookingGlassView())
                {
                    ConfigureGahyeonMacIOSurfaceQuilt(CurrentViewIndex, LookingGlassViewCount);
                    LastGPUSequence = GPUSequence;
                    bGPUViewPrepared = true;
                }
            }
            return true;
        }
        if (!FrameGrabber && GEngine && GEngine->GameViewport && FSlateApplication::IsInitialized())
        {
            TSharedPtr<SViewport> ViewportWidget = FSlateApplication::Get().GetGameViewport();
            TSharedPtr<FSceneViewport> Viewport = ViewportWidget.IsValid()
                ? StaticCastSharedPtr<FSceneViewport>(ViewportWidget->GetViewportInterface().Pin())
                : nullptr;
            if (Viewport.IsValid())
            {
                FrameGrabber = MakeUnique<FFrameGrabber>(Viewport.ToSharedRef(), FIntPoint(FrameWidth, FrameHeight), PF_B8G8R8A8, 3);
                FrameGrabber->StartCapturingFrames();
                UE_LOG(LogTemp, Display, TEXT("Gahyeon direct-alpha bridge started"));
            }
        }
        if (!FrameGrabber)
        {
            return true;
        }

        TArray<FCapturedFrameData> Frames = FrameGrabber->GetCapturedFrames();
        if (Frames.Num() > 0)
        {
            Publish(Frames.Last(), PendingViewIndex);
            bCapturePending = false;
            CurrentViewIndex = (CurrentViewIndex + 1) % LookingGlassViewCount;
        }
        if (bEnableLookingGlassQuilt && !PrepareLookingGlassView())
        {
            return true;
        }
        if (bCapturePending)
        {
            return true;
        }
        CaptureAccumulator += DeltaSeconds;
        if (CaptureAccumulator >= 1.0 / 30.0)
        {
            CaptureAccumulator = 0.0;
            PendingViewIndex = bEnableLookingGlassQuilt ? CurrentViewIndex : 0;
            FrameGrabber->CaptureThisFrame(nullptr);
            bCapturePending = true;
        }
#endif
        return true;
    }

    bool PrepareLookingGlassView()
    {
        if (!GEngine || !GEngine->GameViewport) return false;
        UWorld* World = GEngine->GameViewport->GetWorld();
        if (!World) return false;
        if (!LookingGlassCamera.IsValid())
        {
            for (TActorIterator<ACameraActor> It(World); It; ++It)
            {
                if (!It->IsHidden())
                {
                LookingGlassCamera = *It;
                OriginalCameraLocation = It->GetActorLocation();
                OriginalCameraRotation = It->GetActorRotation();
                if (UCineCameraComponent* CineCamera = Cast<UCineCameraComponent>(
                        It->GetCameraComponent()))
                {
                    OriginalSensorHorizontalOffset = CineCamera->Filmback.SensorHorizontalOffset;
                    OriginalProjectionOffset = CineCamera->GetHorizontalProjectionOffset();
                }
                else
                {
                    UE_LOG(LogTemp, Error,
                        TEXT("Gahyeon Looking Glass requires a CineCameraActor for off-axis projection"));
                    return false;
                }
                    break;
                }
            }
            ASkeletalMeshActor* Character = nullptr;
            for (TActorIterator<ASkeletalMeshActor> It(World); It; ++It)
            {
                if (!It->IsHidden()) { Character = *It; break; }
            }
            if (!LookingGlassCamera.IsValid() || !Character) return false;
            FVector Extent;
            Character->GetActorBounds(false, LookingGlassFocus, Extent, true);
            UE_LOG(LogTemp, Display,
                TEXT("Gahyeon Looking Glass %u-view GPU capture active: cone=%.1f degrees"),
                LookingGlassViewCount,
                LookingGlassViewConeDegrees);
        }
        const float ViewT = (float(CurrentViewIndex) / float(LookingGlassViewCount - 1)) * 2.0f - 1.0f;
        const FVector Forward = OriginalCameraRotation.Vector();
        const FVector Right = FRotationMatrix(OriginalCameraRotation).GetUnitAxis(EAxis::Y);
        const float FocusDistance = FVector::DotProduct(
            LookingGlassFocus - OriginalCameraLocation, Forward);
        if (FocusDistance <= KINDA_SMALL_NUMBER) return false;
        const float ViewAngle = FMath::DegreesToRadians(
            ViewT * LookingGlassViewConeDegrees * 0.5f);
        const float LateralOffset = FocusDistance * FMath::Tan(ViewAngle);
        const FVector ViewLocation = OriginalCameraLocation + Right * LateralOffset;
        LookingGlassCamera->SetActorLocation(ViewLocation);
        LookingGlassCamera->SetActorRotation(OriginalCameraRotation);
        UCineCameraComponent* CameraComponent = Cast<UCineCameraComponent>(
            LookingGlassCamera->GetCameraComponent());
        if (!CameraComponent) return false;
        const float HalfFov = FMath::DegreesToRadians(CameraComponent->FieldOfView * 0.5f);
        const float FocusHalfWidth = FocusDistance * FMath::Tan(HalfFov);
        if (FocusHalfWidth <= KINDA_SMALL_NUMBER) return false;
        CameraComponent->Filmback.SensorHorizontalOffset = OriginalSensorHorizontalOffset;
        const float BaseProjectionOffset = CameraComponent->GetHorizontalProjectionOffset();
        CameraComponent->Filmback.SensorHorizontalOffset = OriginalSensorHorizontalOffset + 1.0f;
        const float ProjectionOffsetPerMillimeter =
            CameraComponent->GetHorizontalProjectionOffset() - BaseProjectionOffset;
        if (FMath::IsNearlyZero(ProjectionOffsetPerMillimeter)) return false;
        const float DesiredProjectionOffset = OriginalProjectionOffset
            - LateralOffset / FocusHalfWidth;
        CameraComponent->Filmback.SensorHorizontalOffset = OriginalSensorHorizontalOffset
            + (DesiredProjectionOffset - BaseProjectionOffset) / ProjectionOffsetPerMillimeter;
        return true;
    }

    void ApplyOverlayControl()
    {
        if (!ControlRegion || !GEngine || !GEngine->GameViewport)
        {
            return;
        }
        auto* Control = static_cast<FSharedOverlayControl*>(ControlRegion->GetAddress());
        if (Control->Magic != ControlMagic || Control->Sequence == LastControlSequence)
        {
            return;
        }
        UWorld* World = GEngine->GameViewport->GetWorld();
        if (!World)
        {
            return;
        }
        ASkeletalMeshActor* Character = nullptr;
        for (TActorIterator<ASkeletalMeshActor> It(World); It; ++It)
        {
            if (!It->IsHidden())
            {
                Character = *It;
                break;
            }
        }
        if (!Character)
        {
            return;
        }
        const float Yaw = FMath::Clamp(Control->YawDegrees, -75.0f, 75.0f);
        FRotator Rotation = Character->GetActorRotation();
        float* InitialYaw = InitialCharacterYaw.Find(Character);
        if (!InitialYaw)
        {
            InitialYaw = &InitialCharacterYaw.Add(Character, Rotation.Yaw);
        }
        Rotation.Yaw = *InitialYaw + Yaw;
        Character->SetActorRotation(Rotation);
        LastControlSequence = Control->Sequence;
    }

    void Publish(const FCapturedFrameData& Frame, uint32 ViewIndex)
    {
        if (!SharedRegion || Frame.ColorBuffer.Num() != FrameWidth * FrameHeight)
        {
            return;
        }
        auto* Header = static_cast<FSharedFrameHeader*>(SharedRegion->GetAddress());
        const uint32 NextBuffer = 1u - Header->ActiveBuffer;
        uint8* Destination = static_cast<uint8*>(SharedRegion->GetAddress()) + HeaderBytes + FrameBytes * NextBuffer;
        FColor* Output = reinterpret_cast<FColor*>(Destination);
        ParallelFor(FrameHeight, [&Frame, Output](int32 Y)
        {
            const int32 RowStart = Y * FrameWidth;
            for (int32 X = 0; X < FrameWidth; ++X)
            {
                const int32 Index = RowStart + X;
                const FColor Source = Frame.ColorBuffer[Index];
                const uint8 Alpha = 255 - Source.A;
                Output[Index] = FColor(
                    uint8((uint16(Source.R) * Alpha) / 255),
                    uint8((uint16(Source.G) * Alpha) / 255),
                    uint8((uint16(Source.B) * Alpha) / 255),
                    Alpha);
            }
        });
        FPlatformMisc::MemoryBarrier();
        Header->AlphaMin = 0;
        Header->AlphaMax = 255;
        Header->BoundsMinX = uint32(FrameWidth * 0.25);
        Header->BoundsMinY = uint32(FrameHeight * 0.12);
        Header->BoundsMaxX = uint32(FrameWidth * 0.70);
        Header->BoundsMaxY = uint32(FrameHeight * 0.89);
        Header->ViewIndex = ViewIndex;
        Header->ViewCount = bEnableLookingGlassQuilt ? LookingGlassViewCount : 1;
        Header->ActiveBuffer = NextBuffer;
        ++Header->Sequence;
        if ((Header->Sequence % 300) == 1)
        {
            UE_LOG(LogTemp, Display, TEXT("Gahyeon parallel direct-alpha frame %llu"), Header->Sequence);
        }
    }

    FTSTicker::FDelegateHandle TickHandle;
    TUniquePtr<FFrameGrabber> FrameGrabber;
    FPlatformMemory::FSharedMemoryRegion* SharedRegion = nullptr;
    FPlatformMemory::FSharedMemoryRegion* ControlRegion = nullptr;
    TMap<TWeakObjectPtr<ASkeletalMeshActor>, float> InitialCharacterYaw;
    TWeakObjectPtr<ACameraActor> LookingGlassCamera;
    FVector OriginalCameraLocation = FVector::ZeroVector;
    FRotator OriginalCameraRotation = FRotator::ZeroRotator;
    float OriginalProjectionOffset = 0.0f;
    float OriginalSensorHorizontalOffset = 0.0f;
    FVector LookingGlassFocus = FVector::ZeroVector;
    uint32 LookingGlassViewCount = 66;
    float LookingGlassViewConeDegrees = 54.0f;
    uint64 LastControlSequence = 0;
    uint32 CurrentViewIndex = 0;
    uint32 PendingViewIndex = 0;
    bool bCapturePending = false;
    bool bEnableLookingGlassQuilt = false;
    bool bGPUViewPrepared = false;
    uint64 LastGPUSequence = 0;
    double CaptureAccumulator = 0.0;
};

IMPLEMENT_MODULE(FGahyeonDesktopMetaHumanPOCModule, GahyeonDesktopMetaHumanPOC)
