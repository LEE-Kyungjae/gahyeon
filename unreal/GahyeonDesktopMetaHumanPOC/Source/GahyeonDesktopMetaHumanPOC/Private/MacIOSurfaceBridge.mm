#include "MacIOSurfaceBridge.h"

#if PLATFORM_MAC
#include "Framework/Application/SlateApplication.h"
#include "Rendering/SlateRenderer.h"
#include "RHIResources.h"
#include "RHICommandList.h"
#include "RHIGPUReadback.h"
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
    volatile uint64 ConsumerSequence = 0;
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
TAtomic<uint64> RequestedViewGeneration(0);
TAtomic<uint64> PublishedViewGeneration(0);
TUniquePtr<FRHIGPUTextureReadback> Readback;
bool bReadbackPending = false;
uint64 ReadbackGeneration = 0;
uint32 ReadbackView = 0, ReadbackViews = 1, ReadbackWidth = 0, ReadbackHeight = 0;
uint32 ReadbackPixelBytes = 0;
MTLPixelFormat ReadbackFormat = MTLPixelFormatInvalid;
id<MTLTexture> ReadbackUpload = nil;

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

void OnStableBackBuffer(ISlateViewportProvider& ViewportProvider)
{
    auto* Header = SharedRegion
        ? static_cast<FIOSurfaceHeader*>(SharedRegion->GetAddress()) : nullptr;
    if (!Header) return;
    if (bReadbackPending)
    {
        if (!Readback->IsReady()) return;
        int32 RowPixels = 0, BufferHeight = 0;
        void* Bytes = Readback->Lock(RowPixels, &BufferHeight);
        if (!Bytes || RowPixels < int32(ReadbackWidth) || BufferHeight < int32(ReadbackHeight))
        {
            UE_LOG(LogTemp, Error, TEXT("Looking Glass GPU readback layout invalid"));
            if (Bytes) Readback->Unlock();
            bReadbackPending = false;
            return;
        }
        if (!ReadbackUpload || ReadbackUpload.width != ReadbackWidth
            || ReadbackUpload.height != ReadbackHeight || ReadbackUpload.pixelFormat != ReadbackFormat)
        {
            MTLTextureDescriptor* Descriptor = [MTLTextureDescriptor
                texture2DDescriptorWithPixelFormat:ReadbackFormat width:ReadbackWidth
                height:ReadbackHeight mipmapped:NO];
            Descriptor.storageMode = MTLStorageModeShared;
            Descriptor.usage = MTLTextureUsageShaderRead;
            ReadbackUpload = [MTLCreateSystemDefaultDevice() newTextureWithDescriptor:Descriptor];
        }
        if (!ReadbackUpload) { Readback->Unlock(); bReadbackPending = false; return; }
        [ReadbackUpload replaceRegion:MTLRegionMake2D(0, 0, ReadbackWidth, ReadbackHeight)
            mipmapLevel:0 withBytes:Bytes bytesPerRow:RowPixels * ReadbackPixelBytes];
        Readback->Unlock();
        if ((!SharedTexture || SharedTexture.width != ReadbackWidth || SharedTexture.height != ReadbackHeight)
            && !CreateGPU(ReadbackUpload)) { bReadbackPending = false; return; }
        // This queue reads our completed CPU upload, never Unreal's live back buffer.
        id<MTLCommandBuffer> Command = [Queue commandBuffer];
        id<MTLComputeCommandEncoder> Encoder = [Command computeCommandEncoder];
        [Encoder setComputePipelineState:Pipeline];
        [Encoder setTexture:ReadbackUpload atIndex:0]; [Encoder setTexture:SharedTexture atIndex:1];
        [Encoder dispatchThreads:MTLSizeMake(ReadbackWidth, ReadbackHeight, 1)
            threadsPerThreadgroup:MTLSizeMake(16, 16, 1)];
        [Encoder endEncoding]; [Command commit]; [Command waitUntilCompleted];
        if (Command.status != MTLCommandBufferStatusCompleted) { bReadbackPending = false; return; }
        Header->ViewIndex = ReadbackView; Header->ViewCount = ReadbackViews;
        FPlatformMisc::MemoryBarrier();
        PublishedViewGeneration.Store(ReadbackGeneration);
        ++Header->Sequence;
        bReadbackPending = false;
        return;
    }
    if (Header->Sequence != Header->ConsumerSequence) return;
    const uint64 Generation = RequestedViewGeneration.Load();
    if (Generation == PublishedViewGeneration.Load()) return;
    FRHITexture* BackBuffer = ViewportProvider.GetBackBufferResource();
    if (!BackBuffer) return;
    if (!Readback) Readback = MakeUnique<FRHIGPUTextureReadback>(TEXT("GahyeonQuiltReadback"));
    ReadbackWidth = BackBuffer->GetSizeXYZ().X; ReadbackHeight = BackBuffer->GetSizeXYZ().Y;
    ReadbackPixelBytes = GPixelFormats[BackBuffer->GetFormat()].BlockBytes;
    ReadbackFormat = MTLPixelFormat(GPixelFormats[BackBuffer->GetFormat()].PlatformFormat);
    id<MTLTexture> Native = (__bridge id<MTLTexture>)BackBuffer->GetNativeResource();
    if (Native) ReadbackFormat = Native.pixelFormat;
    ReadbackGeneration = Generation;
    ReadbackView = RequestedViewIndex.Load(); ReadbackViews = RequestedViewCount.Load();
    Readback->EnqueueCopy(FRHICommandListExecutor::GetImmediateCommandList(), BackBuffer);
    bReadbackPending = true;
}

void OnBackBuffer(SWindow&, ISlateViewportProvider& ViewportProvider)
{
    @autoreleasepool {
        if (FPlatformMisc::GetEnvironmentVariable(TEXT("GAHYEON_LOOKING_GLASS_STABLE_CAPTURE")) == TEXT("1"))
        {
            OnStableBackBuffer(ViewportProvider);
            return;
        }
        if (CopyInFlight.Exchange(true)) return;
        auto* Header = SharedRegion
            ? static_cast<FIOSurfaceHeader*>(SharedRegion->GetAddress()) : nullptr;
        if (!Header || Header->Sequence != Header->ConsumerSequence)
        {
            CopyInFlight.Store(false);
            return;
        }
        const uint64 ViewGeneration = RequestedViewGeneration.Load();
        if (ViewGeneration == PublishedViewGeneration.Load())
        {
            CopyInFlight.Store(false);
            return;
        }
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
        const uint32 ViewIndex = RequestedViewIndex.Load();
        const uint32 ViewCount = RequestedViewCount.Load();
        [Command addCompletedHandler:^(id<MTLCommandBuffer>){
            Header->ViewIndex = ViewIndex;
            Header->ViewCount = ViewCount;
            FPlatformMisc::MemoryBarrier();
            PublishedViewGeneration.Store(ViewGeneration);
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
    Readback.Reset(); ReadbackUpload = nil; bReadbackPending = false;
    ReleaseGPU();
    if (SharedRegion) { FPlatformMemory::UnmapNamedSharedMemoryRegion(SharedRegion); SharedRegion = nullptr; }
}

void ConfigureGahyeonMacIOSurfaceQuilt(uint32 ViewIndex, uint32 ViewCount)
{
    RequestedViewIndex.Store(ViewIndex);
    RequestedViewCount.Store(FMath::Max(1u, ViewCount));
    ++RequestedViewGeneration;
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
