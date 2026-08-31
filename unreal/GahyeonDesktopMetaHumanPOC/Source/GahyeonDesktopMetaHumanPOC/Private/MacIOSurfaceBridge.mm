#include "MacIOSurfaceBridge.h"

#if PLATFORM_MAC
#include "Framework/Application/SlateApplication.h"
#include "Rendering/SlateRenderer.h"
#include "RHIResources.h"
#include "HAL/PlatformMemory.h"
#include "Mac/MacSystemIncludes.h"
#include "Slate/SlateViewportProvider.h"
#include "Templates/Atomic.h"
#import <IOSurface/IOSurface.h>
#import <Metal/Metal.h>

namespace
{
struct alignas(64) FIOSurfaceHeader
{
    uint32 Magic = 0x4748494f; // GHIO
    uint32 Version = 1;
    uint32 SurfaceID = 0;
    uint32 Width = 0;
    uint32 Height = 0;
    uint32 CropMinX = 0;
    uint32 CropMinY = 0;
    uint32 CropMaxX = 0;
    uint32 CropMaxY = 0;
    volatile uint64 Sequence = 0;
    volatile uint32 ViewIndex = 0;
    volatile uint32 ViewCount = 1;
    uint8 Reserved[8] = {};
};
static_assert(sizeof(FIOSurfaceHeader) == 64);

FDelegateHandle DelegateHandle;
FPlatformMemory::FSharedMemoryRegion* SharedRegion = nullptr;
IOSurfaceRef Surface = nullptr;
id<MTLTexture> SharedTexture = nil;
id<MTLComputePipelineState> Pipeline = nil;
id<MTLCommandQueue> Queue = nil;
TAtomic<bool> CopyInFlight(false);
TAtomic<uint32> RequestedViewIndex(0);
TAtomic<uint32> RequestedViewCount(1);

void ReleaseGPU()
{
    SharedTexture = nil; Pipeline = nil; Queue = nil;
    if (Surface) { CFRelease(Surface); Surface = nullptr; }
}

bool CreateGPU(id<MTLTexture> Source)
{
    ReleaseGPU();
    const uint32 Width = uint32(Source.width), Height = uint32(Source.height);
    NSDictionary* Properties = @{
        (id)kIOSurfaceWidth: @(Width), (id)kIOSurfaceHeight: @(Height),
        (id)kIOSurfaceBytesPerElement: @4, (id)kIOSurfaceBytesPerRow: @(Width * 4),
        (id)kIOSurfacePixelFormat: @(uint32('BGRA')), (id)kIOSurfaceIsGlobal: @YES
    };
    Surface = IOSurfaceCreate((CFDictionaryRef)Properties);
    if (!Surface) return false;
    MTLTextureDescriptor* Descriptor = [MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatBGRA8Unorm width:Width height:Height mipmapped:NO];
    Descriptor.usage = MTLTextureUsageShaderRead | MTLTextureUsageShaderWrite;
    Descriptor.storageMode = MTLStorageModeShared;
    SharedTexture = [Source.device newTextureWithDescriptor:Descriptor iosurface:Surface plane:0];
    Queue = [Source.device newCommandQueue];
    NSError* Error = nil;
    NSString* Code = @"#include <metal_stdlib>\nusing namespace metal; kernel void gahyeonAlpha(texture2d<float, access::read> src [[texture(0)]], texture2d<float, access::write> dst [[texture(1)]], uint2 p [[thread_position_in_grid]]) { if (p.x >= dst.get_width() || p.y >= dst.get_height()) return; float4 c=src.read(p); float a=1.0-c.a; dst.write(float4(c.rgb*a,a),p); }";
    id<MTLLibrary> Library = [Source.device newLibraryWithSource:Code options:nil error:&Error];
    Pipeline = Library ? [Source.device newComputePipelineStateWithFunction:[Library newFunctionWithName:@"gahyeonAlpha"] error:&Error] : nil;
    if (!SharedTexture || !Queue || !Pipeline) { UE_LOG(LogTemp, Error, TEXT("Gahyeon IOSurface Metal setup failed: %s"), *FString(Error.localizedDescription)); ReleaseGPU(); return false; }
    auto* Header = static_cast<FIOSurfaceHeader*>(SharedRegion->GetAddress());
    Header->SurfaceID = IOSurfaceGetID(Surface); Header->Width = Width; Header->Height = Height;
    Header->CropMinX = uint32(Width * 0.25); Header->CropMaxX = uint32(Width * 0.70);
    Header->CropMinY = uint32(Height * 0.12); Header->CropMaxY = uint32(Height * 0.89);
    UE_LOG(LogTemp, Display, TEXT("Gahyeon IOSurface ready id=%u size=%ux%u"), Header->SurfaceID, Width, Height);
    return true;
}

void OnBackBuffer(SWindow&, ISlateViewportProvider& ViewportProvider)
{
    @autoreleasepool {
        if (CopyInFlight.Exchange(true)) return;
        FRHITexture* BackBuffer = ViewportProvider.GetBackBufferResource();
        id<MTLTexture> Source = BackBuffer ? (__bridge id<MTLTexture>)BackBuffer->GetNativeResource() : nil;
        if (!Source || !SharedRegion) { CopyInFlight.Store(false); return; }
        if (!SharedTexture || SharedTexture.width != Source.width || SharedTexture.height != Source.height)
            if (!CreateGPU(Source)) { CopyInFlight.Store(false); return; }
        id<MTLCommandBuffer> Command = [Queue commandBuffer];
        id<MTLComputeCommandEncoder> Encoder = [Command computeCommandEncoder];
        [Encoder setComputePipelineState:Pipeline]; [Encoder setTexture:Source atIndex:0]; [Encoder setTexture:SharedTexture atIndex:1];
        MTLSize Group = MTLSizeMake(16, 16, 1), Grid = MTLSizeMake(Source.width, Source.height, 1);
        [Encoder dispatchThreads:Grid threadsPerThreadgroup:Group]; [Encoder endEncoding];
        auto* Header = static_cast<FIOSurfaceHeader*>(SharedRegion->GetAddress());
        const uint32 ViewIndex = RequestedViewIndex.Load();
        const uint32 ViewCount = RequestedViewCount.Load();
        [Command addCompletedHandler:^(id<MTLCommandBuffer>){
            Header->ViewIndex = ViewIndex;
            Header->ViewCount = ViewCount;
            FPlatformMisc::MemoryBarrier();
            ++Header->Sequence;
            CopyInFlight.Store(false);
        }];
        [Command commit];
    }
}
}

void StartGahyeonMacIOSurfaceBridge()
{
    SharedRegion = FPlatformMemory::MapNamedSharedMemoryRegion(TEXT("gahyeon_iosurface_v001"), true, FPlatformMemory::ESharedMemoryAccess::Read | FPlatformMemory::ESharedMemoryAccess::Write, 64);
    if (!SharedRegion) return;
    FMemory::Memzero(SharedRegion->GetAddress(), 64); new (SharedRegion->GetAddress()) FIOSurfaceHeader();
    DelegateHandle = FSlateApplication::Get().GetRenderer()->OnBackBufferReadyToPresent().AddStatic(&OnBackBuffer);
}

void StopGahyeonMacIOSurfaceBridge()
{
    if (DelegateHandle.IsValid() && FSlateApplication::IsInitialized()) FSlateApplication::Get().GetRenderer()->OnBackBufferReadyToPresent().Remove(DelegateHandle);
    ReleaseGPU();
    if (SharedRegion) { FPlatformMemory::UnmapNamedSharedMemoryRegion(SharedRegion); SharedRegion = nullptr; }
}

void ConfigureGahyeonMacIOSurfaceQuilt(uint32 ViewIndex, uint32 ViewCount)
{
    RequestedViewIndex.Store(ViewIndex);
    RequestedViewCount.Store(FMath::Max(1u, ViewCount));
}

uint64 GetGahyeonMacIOSurfaceSequence()
{
    if (!SharedRegion) return 0;
    FPlatformMisc::MemoryBarrier();
    return static_cast<FIOSurfaceHeader*>(SharedRegion->GetAddress())->Sequence;
}
#else
void StartGahyeonMacIOSurfaceBridge() {}
void StopGahyeonMacIOSurfaceBridge() {}
void ConfigureGahyeonMacIOSurfaceQuilt(uint32, uint32) {}
uint64 GetGahyeonMacIOSurfaceSequence() { return 0; }
#endif
