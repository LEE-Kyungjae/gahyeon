#import <AppKit/AppKit.h>
#import <Foundation/Foundation.h>
#import <IOSurface/IOSurface.h>
#import <Metal/Metal.h>

#include "bridge.h"
#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <fcntl.h>
#include <signal.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <thread>
#include <unistd.h>

namespace {
constexpr uint32_t SurfaceMagic = 0x4748494f;
constexpr size_t QuiltColumns = 11, QuiltRows = 6;
constexpr size_t TileWidth = 372, TileHeight = 682;
constexpr size_t OutputWidth = QuiltColumns * TileWidth;
constexpr size_t OutputHeight = QuiltRows * TileHeight;
std::atomic<bool> Running{true};

struct SurfaceHeader {
    uint32_t magic, version, surfaceID, width, height;
    uint32_t cropMinX, cropMinY, cropMaxX, cropMaxY;
    uint64_t sequence;
    uint32_t viewIndex, viewCount;
    uint8_t reserved[8];
};
static_assert(sizeof(SurfaceHeader) == 64);

struct ComposeParameters {
    uint32_t viewIndex, copiesPerView;
    uint32_t cropMinX, cropMinY, cropMaxX, cropMaxY;
};

void Stop(int) { Running.store(false); }
void PumpAppEvents() {
    while (NSEvent* event = [NSApp nextEventMatchingMask:NSEventMaskAny
                                                untilDate:[NSDate distantPast]
                                                   inMode:NSDefaultRunLoopMode dequeue:YES]) {
        [NSApp sendEvent:event];
    }
    [NSApp updateWindows];
}
}

int main() {
    signal(SIGINT, Stop); signal(SIGTERM, Stop);
    [NSApplication sharedApplication];
    [NSApp setActivationPolicy:NSApplicationActivationPolicyAccessory];
    [NSApp finishLaunching];
    id<MTLDevice> device = MTLCreateSystemDefaultDevice();
    if (!device || !initialize_bridge("Gahyeon Looking Glass GPU")) return 4;
    WINDOW_HANDLE window = 0;
    if (!instance_window_metal((__bridge void*)device, &window, FIRST_LOOKING_GLASS_DEVICE)) {
        uninitialize_bridge(); return 5;
    }
    set_window_polling(window, true);
    std::fprintf(stderr, "GAHYEON_LKG_METAL_READY gpu_iosurface=1\n");

    MTLTextureDescriptor* outputDescriptor = [MTLTextureDescriptor
        texture2DDescriptorWithPixelFormat:MTLPixelFormatRGBA8Unorm
        width:OutputWidth height:OutputHeight mipmapped:NO];
    outputDescriptor.usage = MTLTextureUsageShaderRead | MTLTextureUsageShaderWrite;
    outputDescriptor.storageMode = MTLStorageModeShared;
    void* outputRaw = nullptr;
    if (!create_metal_texture_with_iosurface(window, (__bridge void*)outputDescriptor, &outputRaw)) {
        uninitialize_bridge(); return 6;
    }
    id<MTLTexture> output = (__bridge id<MTLTexture>)outputRaw;
    id<MTLCommandQueue> queue = [device newCommandQueue];
    NSString* shader = @"#include <metal_stdlib>\nusing namespace metal;\n"
        "struct P { uint viewIndex, copiesPerView, cropMinX, cropMinY, cropMaxX, cropMaxY; };\n"
        "kernel void compose(texture2d<float, access::read> src [[texture(0)]], texture2d<float, access::write> dst [[texture(1)]], constant P& p [[buffer(0)]], uint3 g [[thread_position_in_grid]]) {\n"
        " if (g.x>=372 || g.y>=682 || g.z>=p.copiesPerView) return;\n"
        " uint slot=p.viewIndex*p.copiesPerView+g.z; uint2 out=uint2((slot%11)*372+g.x,(slot/11)*682+g.y);\n"
        " float cw=max(1.0,float(p.cropMaxX-p.cropMinX)), ch=max(1.0,float(p.cropMaxY-p.cropMinY));\n"
        " float scale=min(372.0/cw,682.0/ch), fw=cw*scale, fh=ch*scale;\n"
        " float2 q=float2(g.xy)-float2((372.0-fw)*0.5,(682.0-fh)*0.5);\n"
        " if(q.x<0||q.y<0||q.x>=fw||q.y>=fh){dst.write(float4(0,0,0,1),out);return;}\n"
        " uint2 s=uint2(float2(p.cropMinX,p.cropMinY)+q/scale); float4 c=src.read(s);\n"
        " dst.write(float4(c.rgb,1),out);\n} ";
    NSError* error = nil;
    id<MTLLibrary> library = [device newLibraryWithSource:shader options:nil error:&error];
    id<MTLComputePipelineState> pipeline = library
        ? [device newComputePipelineStateWithFunction:[library newFunctionWithName:@"compose"] error:&error] : nil;
    if (!queue || !pipeline) {
        std::fprintf(stderr, "GAHYEON_LKG_GPU_SHADER_FAILED %s\n", error.localizedDescription.UTF8String ?: "unknown");
        release_metal_texture(window, outputRaw); uninitialize_bridge(); return 7;
    }

    int fd = -1;
    while (Running.load() && fd < 0) {
        fd = shm_open("/gahyeon_iosurface_v001", O_RDONLY, 0);
        if (fd < 0) std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }
    auto* header = fd >= 0 ? static_cast<SurfaceHeader*>(mmap(nullptr, 64, PROT_READ, MAP_SHARED, fd, 0)) : nullptr;
    if (!header || header == MAP_FAILED) return 8;

    uint64_t lastSequence = 0;
    uint32_t activeSurfaceID = 0;
    IOSurfaceRef surface = nullptr;
    id<MTLTexture> input = nil;
    bool shown = false;
    auto lastPresented = std::chrono::steady_clock::now();
    while (Running.load()) @autoreleasepool {
        PumpAppEvents();
        if (header->magic != SurfaceMagic || header->sequence == 0 || header->sequence == lastSequence) {
            std::this_thread::sleep_for(std::chrono::milliseconds(1)); continue;
        }
        if (header->surfaceID != activeSurfaceID) {
            input = nil;
            if (surface) CFRelease(surface);
            surface = IOSurfaceLookup(header->surfaceID);
            if (!surface) { std::this_thread::sleep_for(std::chrono::milliseconds(10)); continue; }
            MTLTextureDescriptor* descriptor = [MTLTextureDescriptor
                texture2DDescriptorWithPixelFormat:MTLPixelFormatBGRA8Unorm
                width:header->width height:header->height mipmapped:NO];
            descriptor.usage = MTLTextureUsageShaderRead; descriptor.storageMode = MTLStorageModeShared;
            input = [device newTextureWithDescriptor:descriptor iosurface:surface plane:0];
            activeSurfaceID = header->surfaceID;
        }
        const uint32_t viewCount = header->viewCount;
        if (!input || viewCount == 0 || viewCount > QuiltColumns * QuiltRows
            || (QuiltColumns * QuiltRows) % viewCount != 0 || header->viewIndex >= viewCount) {
            lastSequence = header->sequence; continue;
        }
        ComposeParameters parameters{header->viewIndex, uint32_t((QuiltColumns * QuiltRows) / viewCount),
            header->cropMinX, header->cropMinY, header->cropMaxX, header->cropMaxY};
        id<MTLCommandBuffer> command = [queue commandBuffer];
        id<MTLComputeCommandEncoder> encoder = [command computeCommandEncoder];
        [encoder setComputePipelineState:pipeline];
        [encoder setTexture:input atIndex:0]; [encoder setTexture:output atIndex:1];
        [encoder setBytes:&parameters length:sizeof(parameters) atIndex:0];
        [encoder dispatchThreads:MTLSizeMake(TileWidth, TileHeight, parameters.copiesPerView)
            threadsPerThreadgroup:MTLSizeMake(16, 16, 1)];
        [encoder endEncoding]; [command commit]; [command waitUntilCompleted];
        if (header->viewIndex + 1 == viewCount) {
            if (!draw_interop_quilt_texture_metal(window, outputRaw, QuiltColumns, QuiltRows, 0.5625f, 1.0f)) break;
            if (!shown) shown = show_window(window, true);
            const auto now = std::chrono::steady_clock::now();
            const auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(now - lastPresented).count();
            std::fprintf(stderr, "GAHYEON_LKG_GPU_QUILT interval_ms=%lld shown=%d\n", static_cast<long long>(ms), shown);
            lastPresented = now;
        }
        lastSequence = header->sequence;
    }
    show_window(window, false);
    if (surface) CFRelease(surface);
    munmap(header, 64); close(fd);
    release_metal_texture(window, outputRaw); uninitialize_bridge();
    return 0;
}
