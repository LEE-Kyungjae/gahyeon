#import <AppKit/AppKit.h>
#import <Foundation/Foundation.h>
#import <IOSurface/IOSurface.h>
#import <Metal/Metal.h>
#import <OpenGL/OpenGL.h>

#include "bridge.h"
#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fcntl.h>
#include <signal.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <thread>
#include <unistd.h>
#include <vector>

namespace {
constexpr uint32_t SurfaceMagic = 0x4748494f;
constexpr size_t QuiltColumns = 11, QuiltRows = 6;
constexpr size_t TileWidth = 372, TileHeight = 682;
constexpr size_t OutputWidth = QuiltColumns * TileWidth;
constexpr size_t OutputHeight = QuiltRows * TileHeight;
constexpr size_t AnimatedFrameCount = 12;
constexpr double AnimatedFPS = 12.0;
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
    NSOpenGLPixelFormatAttribute glAttributes[] = {
        NSOpenGLPFAOpenGLProfile, NSOpenGLProfileVersion3_2Core,
        NSOpenGLPFAAccelerated,
        NSOpenGLPFADoubleBuffer,
        0
    };
    NSOpenGLPixelFormat* glPixelFormat = [[NSOpenGLPixelFormat alloc]
        initWithAttributes:glAttributes];
    NSOpenGLContext* glContext = glPixelFormat
        ? [[NSOpenGLContext alloc] initWithFormat:glPixelFormat shareContext:nil] : nil;
    NSWindow* glHostWindow = [[NSWindow alloc]
        initWithContentRect:NSMakeRect(-10000, -10000, 16, 16)
                  styleMask:NSWindowStyleMaskBorderless
                    backing:NSBackingStoreBuffered
                      defer:NO];
    if (!glContext || !glHostWindow) return 3;
    [glContext setView:glHostWindow.contentView];
    [glContext makeCurrentContext];
    [glContext update];
    const bool flatMode = std::getenv("GAHYEON_LOOKING_GLASS_FLAT") != nullptr;
    const bool staticMode = std::getenv("GAHYEON_LOOKING_GLASS_STATIC_QA") != nullptr;
    const bool animatedMode = std::getenv("GAHYEON_LOOKING_GLASS_ANIMATED_QA") != nullptr;
    id<MTLDevice> device = MTLCreateSystemDefaultDevice();
    if (!device || !initialize_bridge("Gahyeon Looking Glass GPU")) return 4;
    WINDOW_HANDLE window = 0;
    if (!instance_window_metal((__bridge void*)device, &window, FIRST_LOOKING_GLASS_DEVICE)) {
        uninitialize_bridge(); return 5;
    }
    set_window_polling(window, true);
    std::fprintf(stderr, "GAHYEON_LKG_METAL_READY gpu_iosurface=1 gl_bootstrap=1\n");

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
    void* blendedRaw = nullptr;
    if (!create_metal_texture_with_iosurface(window, (__bridge void*)outputDescriptor, &blendedRaw)) {
        release_metal_texture(window, outputRaw); uninitialize_bridge(); return 6;
    }
    id<MTLTexture> blended = (__bridge id<MTLTexture>)blendedRaw;
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
        " dst.write(float4(c.rgb,1),out);\n}\n"
        "kernel void blendViews(texture2d<float, access::read> src [[texture(0)]], texture2d<float, access::write> dst [[texture(1)]], uint2 p [[thread_position_in_grid]]) {\n"
        " if(p.x>=src.get_width()||p.y>=src.get_height()) return;\n"
        " uint tx=p.x%372, ty=p.y%682, slot=(p.y/682)*11+p.x/372;\n"
        " float4 c=src.read(p); float4 sum=c*0.88; float weight=0.88;\n"
        " if(slot>0){uint s=slot-1; sum+=src.read(uint2((s%11)*372+tx,(s/11)*682+ty))*0.06; weight+=0.06;}\n"
        " if(slot<65){uint s=slot+1; sum+=src.read(uint2((s%11)*372+tx,(s/11)*682+ty))*0.06; weight+=0.06;}\n"
        " dst.write(sum/weight,p);\n} ";
    NSError* error = nil;
    id<MTLLibrary> library = [device newLibraryWithSource:shader options:nil error:&error];
    id<MTLComputePipelineState> pipeline = library
        ? [device newComputePipelineStateWithFunction:[library newFunctionWithName:@"compose"] error:&error] : nil;
    id<MTLComputePipelineState> blendPipeline = library
        ? [device newComputePipelineStateWithFunction:[library newFunctionWithName:@"blendViews"] error:&error] : nil;
    if (!queue || !pipeline || !blendPipeline) {
        std::fprintf(stderr, "GAHYEON_LKG_GPU_SHADER_FAILED %s\n", error.localizedDescription.UTF8String ?: "unknown");
        release_metal_texture(window, blendedRaw); release_metal_texture(window, outputRaw);
        uninitialize_bridge(); return 7;
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
    bool flatCaptured = false;
    bool staticCaptured = false;
    bool animatedCaptured = false;
    std::vector<void*> animatedFrames;
    auto playbackStarted = std::chrono::steady_clock::now();
    size_t lastPlaybackFrame = AnimatedFrameCount;
    auto lastPresented = std::chrono::steady_clock::now();
    while (Running.load()) @autoreleasepool {
        PumpAppEvents();
        if (animatedCaptured) {
            const double seconds = std::chrono::duration<double>(
                std::chrono::steady_clock::now() - playbackStarted).count();
            const size_t phase = size_t(seconds * AnimatedFPS) % (AnimatedFrameCount * 2 - 2);
            const size_t frame = phase < AnimatedFrameCount
                ? phase : AnimatedFrameCount * 2 - 2 - phase;
            id<MTLTexture> sourceFrame = (__bridge id<MTLTexture>)animatedFrames[frame];
            id<MTLCommandBuffer> playbackCommand = [queue commandBuffer];
            id<MTLBlitCommandEncoder> playbackEncoder = [playbackCommand blitCommandEncoder];
            [playbackEncoder copyFromTexture:sourceFrame sourceSlice:0 sourceLevel:0
                sourceOrigin:MTLOriginMake(0, 0, 0)
                sourceSize:MTLSizeMake(OutputWidth, OutputHeight, 1)
                toTexture:blended destinationSlice:0 destinationLevel:0
                destinationOrigin:MTLOriginMake(0, 0, 0)];
            [playbackEncoder endEncoding];
            [playbackCommand commit];
            [playbackCommand waitUntilCompleted];
            if (!draw_interop_quilt_texture_metal(window, blendedRaw,
                    QuiltColumns, QuiltRows, 0.5625f, 1.0f)) break;
            if (frame != lastPlaybackFrame) {
                std::fprintf(stderr, "GAHYEON_LKG_IDLE_PLAYBACK frame=%zu\n", frame);
                lastPlaybackFrame = frame;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(8)); continue;
        }
        if (staticCaptured) {
            if (!draw_interop_quilt_texture_metal(window, blendedRaw, QuiltColumns, QuiltRows, 0.5625f, 1.0f)) break;
            std::this_thread::sleep_for(std::chrono::milliseconds(8)); continue;
        }
        if (flatCaptured) {
            std::this_thread::sleep_for(std::chrono::milliseconds(10)); continue;
        }
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
        const uint32_t viewIndex = header->viewIndex;
        const uint32_t cropMinX = header->cropMinX, cropMinY = header->cropMinY;
        const uint32_t cropMaxX = header->cropMaxX, cropMaxY = header->cropMaxY;
        if (!input || viewCount == 0 || viewCount > QuiltColumns * QuiltRows
            || (QuiltColumns * QuiltRows) % viewCount != 0 || viewIndex >= viewCount) {
            lastSequence = header->sequence; continue;
        }
        if ((flatMode || staticMode || animatedMode) && viewCount <= 1) {
            lastSequence = header->sequence; continue;
        }
        if (flatMode && viewIndex != viewCount / 2) {
            lastSequence = header->sequence; continue;
        }
        ComposeParameters parameters{flatMode ? 0u : viewIndex,
            flatMode ? uint32_t(QuiltColumns * QuiltRows) : uint32_t((QuiltColumns * QuiltRows) / viewCount),
            cropMinX, cropMinY, cropMaxX, cropMaxY};
        id<MTLCommandBuffer> command = [queue commandBuffer];
        id<MTLComputeCommandEncoder> encoder = [command computeCommandEncoder];
        [encoder setComputePipelineState:pipeline];
        [encoder setTexture:input atIndex:0]; [encoder setTexture:output atIndex:1];
        [encoder setBytes:&parameters length:sizeof(parameters) atIndex:0];
        [encoder dispatchThreads:MTLSizeMake(TileWidth, TileHeight, parameters.copiesPerView)
            threadsPerThreadgroup:MTLSizeMake(16, 16, 1)];
        [encoder endEncoding]; [command commit]; [command waitUntilCompleted];
        if (flatMode || viewIndex + 1 == viewCount) {
            void* presentedTexture = outputRaw;
            if (!flatMode) {
                id<MTLCommandBuffer> blendCommand = [queue commandBuffer];
                id<MTLComputeCommandEncoder> blendEncoder = [blendCommand computeCommandEncoder];
                [blendEncoder setComputePipelineState:blendPipeline];
                [blendEncoder setTexture:output atIndex:0]; [blendEncoder setTexture:blended atIndex:1];
                [blendEncoder dispatchThreads:MTLSizeMake(OutputWidth, OutputHeight, 1)
                    threadsPerThreadgroup:MTLSizeMake(16, 16, 1)];
                [blendEncoder endEncoding]; [blendCommand commit]; [blendCommand waitUntilCompleted];
                presentedTexture = blendedRaw;
                std::fprintf(stderr, "GAHYEON_LKG_VIEW_BLEND center=0.88 adjacent=0.06\n");
            }
            if (animatedMode && !flatMode) {
                void* frameRaw = nullptr;
                if (!create_metal_texture_with_iosurface(
                        window, (__bridge void*)outputDescriptor, &frameRaw)) break;
                id<MTLTexture> frameTexture = (__bridge id<MTLTexture>)frameRaw;
                id<MTLCommandBuffer> copyCommand = [queue commandBuffer];
                id<MTLBlitCommandEncoder> copyEncoder = [copyCommand blitCommandEncoder];
                [copyEncoder copyFromTexture:blended sourceSlice:0 sourceLevel:0
                    sourceOrigin:MTLOriginMake(0, 0, 0)
                    sourceSize:MTLSizeMake(OutputWidth, OutputHeight, 1)
                    toTexture:frameTexture destinationSlice:0 destinationLevel:0
                    destinationOrigin:MTLOriginMake(0, 0, 0)];
                [copyEncoder endEncoding]; [copyCommand commit]; [copyCommand waitUntilCompleted];
                animatedFrames.push_back(frameRaw);
                presentedTexture = frameRaw;
                std::fprintf(stderr, "GAHYEON_LKG_IDLE_FRAME_READY frame=%zu/%zu\n",
                    animatedFrames.size(), AnimatedFrameCount);
                if (animatedFrames.size() == AnimatedFrameCount) {
                    animatedCaptured = true;
                    playbackStarted = std::chrono::steady_clock::now();
                    std::fprintf(stderr,
                        "GAHYEON_LKG_IDLE_LOOP_READY frames=%zu fps=%.1f mode=pingpong\n",
                        animatedFrames.size(), AnimatedFPS);
                }
            }
            if (!draw_interop_quilt_texture_metal(window, presentedTexture, QuiltColumns, QuiltRows, 0.5625f, 1.0f)) break;
            if (!shown) shown = show_window(window, true);
            const auto now = std::chrono::steady_clock::now();
            const auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(now - lastPresented).count();
            std::fprintf(stderr, "GAHYEON_LKG_GPU_QUILT interval_ms=%lld shown=%d\n", static_cast<long long>(ms), shown);
            if (flatMode) {
                flatCaptured = true;
                std::fprintf(stderr, "GAHYEON_LKG_FLAT_IMAGE_READY source_view=%u\n", viewIndex);
            } else if (staticMode) {
                staticCaptured = true;
                std::fprintf(stderr, "GAHYEON_LKG_STATIC_QUILT_READY views=%u\n", viewCount);
            }
            lastPresented = now;
        }
        lastSequence = header->sequence;
    }
    show_window(window, false);
    if (surface) CFRelease(surface);
    munmap(header, 64); close(fd);
    for (void* frameRaw : animatedFrames) release_metal_texture(window, frameRaw);
    release_metal_texture(window, blendedRaw);
    release_metal_texture(window, outputRaw); uninitialize_bridge();
    return 0;
}
