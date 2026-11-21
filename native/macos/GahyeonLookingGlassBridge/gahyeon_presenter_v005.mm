#import <AppKit/AppKit.h>
#import <Foundation/Foundation.h>
#import <IOSurface/IOSurface.h>
#import <Metal/Metal.h>
#import <OpenGL/OpenGL.h>
#import <OpenGL/gl3.h>

#include "bridge.h"
#include "quilt_disk_cache.h"
#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fcntl.h>
#include <future>
#include <pthread.h>
#include <signal.h>
#include <string>
#include <sys/mman.h>
#include <sys/stat.h>
#include <thread>
#include <unistd.h>
#include <vector>

namespace {
constexpr uint32_t SurfaceMagic = 0x4748494f;
constexpr size_t QuiltColumns = 11, QuiltRows = 6;
constexpr size_t TileWidth = 248, TileHeight = 454;
constexpr size_t OutputWidth = QuiltColumns * TileWidth;
constexpr size_t OutputHeight = QuiltRows * TileHeight;
constexpr size_t AnimatedFrameCount = 12;
// This preview samples twelve poses across the source clip's ten seconds.

std::atomic<bool> Running{true};

struct SurfaceHeader {
    uint32_t magic, version, surfaceID, width, height;
    uint32_t cropMinX, cropMinY, cropMaxX, cropMaxY;
    uint64_t sequence;
    uint32_t viewIndex, viewCount;
    volatile uint64_t consumerSequence;
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
    id playbackActivity = [[NSProcessInfo processInfo]
        beginActivityWithOptions:(NSActivityUserInitiatedAllowingIdleSystemSleep | NSActivityLatencyCritical)
        reason:@"Looking Glass character animation"];
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
    const bool glUpload = std::getenv("GAHYEON_LOOKING_GLASS_GL_UPLOAD") != nullptr;
    const char* smoothSetting = std::getenv("GAHYEON_LOOKING_GLASS_SMOOTH_QA");
    const bool smoothMode = smoothSetting && std::string(smoothSetting) == "1";
    if (smoothMode && (!glUpload || !animatedMode || flatMode || staticMode)) return 9;
    const char* probeDirectory = std::getenv("GAHYEON_LOOKING_GLASS_PROBE_DIR");
    const size_t frameCount = smoothMode && !probeDirectory ? 120 : AnimatedFrameCount;
    const char* durationSetting = std::getenv("GAHYEON_LOOKING_GLASS_CLIP_SECONDS");
    const double clipSeconds = durationSetting ? std::strtod(durationSetting, nullptr) : 10.0;
    if (!(clipSeconds > 0.0 && clipSeconds < 3600.0)) return 9;
    const double poseFPS = frameCount / clipSeconds;
    const bool pacedPlayback = glUpload;
    id<MTLDevice> device = MTLCreateSystemDefaultDevice();
    if (!device || !initialize_bridge("Gahyeon Looking Glass GPU")) return 4;
    const char* displaySetting = std::getenv("GAHYEON_LOOKING_GLASS_DISPLAY_ID");
    if (!displaySetting) { uninitialize_bridge(); return 5; }
    char* end = nullptr;
    const unsigned long displayId = std::strtoul(displaySetting, &end, 10);
    if (!end || *end) { uninitialize_bridge(); return 5; }
    float calibratedAspect = 0; int qw = 0, qh = 0, qc = 0, qr = 0;
    if (!get_default_quilt_settings_for_display(displayId, &calibratedAspect, &qw, &qh, &qc, &qr)
        || qw != 4092 || qh != 4092 || qc != QuiltColumns || qr != QuiltRows
        || calibratedAspect != 0.5625f) {
        std::fprintf(stderr, "GAHYEON_LKG_UNSUPPORTED_PROFILE\n"); uninitialize_bridge(); return 5;
    }
    std::fprintf(stderr, "GAHYEON_LKG_SELECTED display=%lu quilt=%dx%d grid=%dx%d aspect=%.4f\n", displayId, qw, qh, qc, qr, calibratedAspect);
    WINDOW_HANDLE window = 0;
    const bool windowReady = glUpload
        ? instance_window_gl(&window, displayId)
        : instance_window_metal((__bridge void*)device, &window, displayId);
    if (!windowReady) {
        uninitialize_bridge(); return 5;
    }
    GLuint uploadTexture = 0;
    std::vector<uint8_t> uploadBytes;
    if (glUpload) {
        [glContext makeCurrentContext];
        glGenTextures(1, &uploadTexture);
        glBindTexture(GL_TEXTURE_2D, uploadTexture);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, OutputWidth, OutputHeight,
            0, GL_RGBA, GL_UNSIGNED_BYTE, nullptr);
        uploadBytes.resize(OutputWidth * OutputHeight * 4);
        glFinish();
    }
    auto presentUpload = [&]() {
            [glContext makeCurrentContext];
            glBindTexture(GL_TEXTURE_2D, uploadTexture);
            glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, OutputWidth, OutputHeight,
                GL_RGBA, GL_UNSIGNED_BYTE, uploadBytes.data());
            glFinish();
            return draw_interop_quilt_texture_gl(window, uploadTexture, PixelFormats::RGBA,
                OutputWidth, OutputHeight, QuiltColumns, QuiltRows, 0.5625f, 1.0f);
    };
    auto presentQuilt = [&](void* texture) {
        if (glUpload) {
            id<MTLTexture> source = (__bridge id<MTLTexture>)texture;
            [source getBytes:uploadBytes.data() bytesPerRow:OutputWidth * 4
                fromRegion:MTLRegionMake2D(0, 0, OutputWidth, OutputHeight) mipmapLevel:0];
            return presentUpload();
        }
        return draw_interop_quilt_texture_metal(window, texture,
            QuiltColumns, QuiltRows, 0.5625f, 1.0f);
    };
    auto createTexture = [&](MTLTextureDescriptor* descriptor, void** texture) {
        if (!glUpload)
            return create_metal_texture_with_iosurface(window, (__bridge void*)descriptor, texture);
        id<MTLTexture> allocated = [device newTextureWithDescriptor:descriptor];
        *texture = (__bridge_retained void*)allocated;
        return allocated != nil;
    };
    auto releaseTexture = [&](void* texture) {
        if (!glUpload) { release_metal_texture(window, texture); return; }
        id released = CFBridgingRelease(texture);
        (void)released;
    };
    set_window_polling(window, true);
    std::fprintf(stderr, "GAHYEON_LKG_METAL_READY gpu_iosurface=1 gl_bootstrap=1\n");

    MTLTextureDescriptor* outputDescriptor = [MTLTextureDescriptor
        texture2DDescriptorWithPixelFormat:MTLPixelFormatRGBA8Unorm
        width:OutputWidth height:OutputHeight mipmapped:NO];
    outputDescriptor.usage = MTLTextureUsageShaderRead | MTLTextureUsageShaderWrite;
    outputDescriptor.storageMode = MTLStorageModeShared;
    void* outputRaw = nullptr;
    if (!createTexture(outputDescriptor, &outputRaw)) {
        uninitialize_bridge(); return 6;
    }
    id<MTLTexture> output = (__bridge id<MTLTexture>)outputRaw;
    void* blendedRaw = nullptr;
    if (!createTexture(outputDescriptor, &blendedRaw)) {
        releaseTexture(outputRaw); uninitialize_bridge(); return 6;
    }
    id<MTLTexture> blended = (__bridge id<MTLTexture>)blendedRaw;
    id<MTLCommandQueue> queue = [device newCommandQueue];
    NSString* shader = @"#include <metal_stdlib>\nusing namespace metal;\n"
        "struct P { uint viewIndex, copiesPerView, cropMinX, cropMinY, cropMaxX, cropMaxY; };\n"
        "kernel void compose(texture2d<float, access::sample> src [[texture(0)]], texture2d<float, access::write> dst [[texture(1)]], constant P& p [[buffer(0)]], uint3 g [[thread_position_in_grid]]) {\n"
        " if (g.x>=248 || g.y>=454 || g.z>=p.copiesPerView) return;\n"
        " uint slot=p.viewIndex*p.copiesPerView+g.z; uint2 out=uint2((slot%11)*248+g.x,(slot/11)*454+g.y);\n"
        " float cw=max(1.0,float(p.cropMaxX-p.cropMinX)), ch=max(1.0,float(p.cropMaxY-p.cropMinY));\n"
        " float2 uv=(float2(g.xy)+0.5)/float2(248.0,454.0);\n"
        " float2 pos=float2(p.cropMinX,p.cropMinY)+uv*float2(cw,ch);\n"
        " constexpr sampler linearSampler(coord::pixel, address::clamp_to_edge, filter::linear);\n"
        " float4 c=src.sample(linearSampler,pos);\n"
        " dst.write(float4(c.rgb,1),out);\n}\n"
        "kernel void blendViews(texture2d<float, access::read> src [[texture(0)]], texture2d<float, access::write> dst [[texture(1)]], uint2 p [[thread_position_in_grid]]) {\n"
        " if(p.x>=src.get_width()||p.y>=src.get_height()) return;\n"
        " dst.write(src.read(p),p);\n} ";
    NSError* error = nil;
    id<MTLLibrary> library = [device newLibraryWithSource:shader options:nil error:&error];
    id<MTLComputePipelineState> pipeline = library
        ? [device newComputePipelineStateWithFunction:[library newFunctionWithName:@"compose"] error:&error] : nil;
    id<MTLComputePipelineState> blendPipeline = library
        ? [device newComputePipelineStateWithFunction:[library newFunctionWithName:@"blendViews"] error:&error] : nil;
    if (!queue || !pipeline || !blendPipeline) {
        std::fprintf(stderr, "GAHYEON_LKG_GPU_SHADER_FAILED %s\n", error.localizedDescription.UTF8String ?: "unknown");
        releaseTexture(blendedRaw); releaseTexture(outputRaw);
        uninitialize_bridge(); return 7;
    }

    uint64_t lastSequence = 0;
    uint32_t activeSurfaceID = 0;
    IOSurfaceRef surface = nullptr;
    id<MTLTexture> input = nil;
    bool shown = false;
    bool flatCaptured = false;
    bool staticCaptured = false;
    bool animatedCaptured = false;
    std::array<bool, QuiltColumns * QuiltRows> quiltCoverage{};
    std::vector<void*> animatedFrames;
    const char* cacheDirectory = std::getenv("GAHYEON_LOOKING_GLASS_CACHE_DIR");
    if (!cacheDirectory) return 9;
    QuiltDiskCache compressedFrames(OutputWidth * OutputHeight * 4, 6ull * 1024 * 1024 * 1024, cacheDirectory);
    const bool cacheOnly = std::getenv("GAHYEON_LOOKING_GLASS_CACHE_ONLY") != nullptr;
    if (!cacheOnly) compressedFrames.discardIncomplete(frameCount);
    if (smoothMode && compressedFrames.size() == frameCount) {
        animatedCaptured = true;
        std::fprintf(stderr, "GAHYEON_LKG_CACHE_RESTORED frames=%zu fps=%.1f\n", frameCount, poseFPS);
    }
    if (cacheOnly && !animatedCaptured) {
        std::fprintf(stderr, "GAHYEON_LKG_CACHE_ONLY_INVALID\n");
        releaseTexture(blendedRaw); releaseTexture(outputRaw); uninitialize_bridge();
        return 9;
    }
    int fd = -1;
    SurfaceHeader* header = nullptr;
    if (!animatedCaptured) {
        while (Running.load() && fd < 0) {
            fd = shm_open("/gahyeon_iosurface_v001", O_RDWR, 0);
            if (fd < 0) std::this_thread::sleep_for(std::chrono::milliseconds(50));
        }
        header = fd >= 0 ? static_cast<SurfaceHeader*>(mmap(
            nullptr, 64, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0)) : nullptr;
        if (!header || header == MAP_FAILED) return 8;
    }
    bool playbackNotified = false;
    bool compressedRetentionConfigured = false;
    int exitCode = 0;
    auto playbackStarted = std::chrono::steady_clock::now();
    size_t lastPlaybackFrame = frameCount;
    size_t smoothPhase = 0;
    std::future<bool> pendingDecode;
    std::vector<uint8_t> decodeBytes(OutputWidth * OutputHeight * 4);
    double nextSmoothTime = 0.0;
    auto lastPresented = std::chrono::steady_clock::now();
    auto lastWaitStatus = std::chrono::steady_clock::now();
    while (Running.load()) @autoreleasepool {
        PumpAppEvents();
        if (animatedCaptured) {
            if (smoothMode && !compressedRetentionConfigured) {
                const char* setting = std::getenv("GAHYEON_LOOKING_GLASS_COMPRESSED_CACHE_MIB");
                char* end = nullptr;
                const unsigned long mib = setting ? std::strtoul(setting, &end, 10) : 0;
                if (mib > 0 && mib <= 1792 && end && !*end
                    && compressedFrames.retainCompressed(frameCount, size_t(mib) * 1024 * 1024)) {
                    std::fprintf(stderr, "GAHYEON_LKG_COMPRESSED_RAM_CACHE bytes=%zu cap_mib=%lu\n", compressedFrames.bytes(), mib);
                }
                compressedRetentionConfigured = true;
            }
            const double seconds = std::chrono::duration<double>(
                std::chrono::steady_clock::now() - playbackStarted).count();
            if (smoothMode && seconds < nextSmoothTime) {
                std::this_thread::sleep_for(std::chrono::milliseconds(1));
                continue;
            }
            const size_t phase = smoothMode ? smoothPhase
                : size_t(seconds * poseFPS) % (frameCount * 2 - 2);
            const size_t frame = phase < frameCount
                ? phase : frameCount * 2 - 2 - phase;
            // Keep pumping window events, but copy/present only when the pose changes.
            // Opt-in until time-separated display captures confirm visible playback.
            if (pacedPlayback && frame == lastPlaybackFrame) {
                std::this_thread::sleep_for(std::chrono::milliseconds(2));
                continue;
            }
            if (pacedPlayback) {
                // Upload each changed cached pose through the verified GL input path.
                if (smoothMode) {
                    const auto decodeStarted = std::chrono::steady_clock::now();
                    if (!pendingDecode.valid()) {
                        pendingDecode = std::async(std::launch::async, [&, frame] {
                            pthread_set_qos_class_self_np(QOS_CLASS_USER_INTERACTIVE, 0);
                            return compressedFrames.decode(frame, decodeBytes.data());
                        });
                    }
                    const bool decoded = pendingDecode.get();
                    if (decoded) uploadBytes.swap(decodeBytes);
                    const size_t followingPhase = (smoothPhase + 1) % (frameCount * 2 - 2);
                    const size_t followingFrame = followingPhase < frameCount ? followingPhase : frameCount * 2 - 2 - followingPhase;
                    pendingDecode = std::async(std::launch::async, [&, followingFrame] {
                        pthread_set_qos_class_self_np(QOS_CLASS_USER_INTERACTIVE, 0);
                        return compressedFrames.decode(followingFrame, decodeBytes.data());
                    });
                    const auto uploadStarted = std::chrono::steady_clock::now();
                    const bool presented = decoded && presentUpload();
                    const auto uploadEnded = std::chrono::steady_clock::now();
                    if (frame % 30 == 0) std::fprintf(stderr, "GAHYEON_LKG_TIMING decode_wait_ms=%.2f upload_ms=%.2f\n",
                        std::chrono::duration<double,std::milli>(uploadStarted-decodeStarted).count(),
                        std::chrono::duration<double,std::milli>(uploadEnded-uploadStarted).count());
                    if (!presented) {
                        std::fprintf(stderr, "GAHYEON_LKG_PLAYBACK_FAILED frame=%zu\n", frame);
                        exitCode = 9; break;
                    }
                } else if (!presentQuilt(animatedFrames[frame])) break;
                if (!shown) shown = show_window(window, true);
                if (!playbackNotified && shown) {
                    const char* readyPath = std::getenv("GAHYEON_LOOKING_GLASS_PLAYBACK_READY_FILE");
                    if (readyPath) {
                        FILE* ready = std::fopen(readyPath, "wb");
                        if (!ready) { exitCode = 9; break; }
                        const bool written = std::fputs("playing\n", ready) >= 0;
                        const bool closed = std::fclose(ready) == 0;
                        if (!written || !closed) { exitCode = 9; break; }
                    }
                    playbackNotified = true;
                }
                std::fprintf(stderr, "GAHYEON_LKG_IDLE_PLAYBACK frame=%zu time=%.6f\n", frame, seconds);
                lastPlaybackFrame = frame;
                if (smoothMode) {
                    // A slow upload must hold time, not skip several skeletal poses or
                    // burst through them to catch up with the wall clock.
                    smoothPhase = (smoothPhase + 1) % (frameCount * 2 - 2);
                    nextSmoothTime = seconds + 1.0 / poseFPS;
                }
                continue;
            }
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
            const auto now = std::chrono::steady_clock::now();
            if (now - lastWaitStatus >= std::chrono::seconds(5)) {
                std::fprintf(stderr,
                    "GAHYEON_LKG_ACK_WAIT sequence=%llu consumer=%llu view=%u/%u last=%llu\n",
                    static_cast<unsigned long long>(header->sequence),
                    static_cast<unsigned long long>(header->consumerSequence),
                    header->viewIndex, header->viewCount,
                    static_cast<unsigned long long>(lastSequence));
                lastWaitStatus = now;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(1)); continue;
        }
        const uint64_t sourceSequence = header->sequence;
        auto acknowledge = [&]() {
            std::atomic_thread_fence(std::memory_order_release);
            header->consumerSequence = sourceSequence;
        };
        if (header->surfaceID != activeSurfaceID) {
            input = nil;
            if (surface) CFRelease(surface);
            surface = IOSurfaceLookup(header->surfaceID);
            if (!surface) {
                lastSequence = sourceSequence;
                acknowledge();
                std::this_thread::sleep_for(std::chrono::milliseconds(10));
                continue;
            }
            MTLTextureDescriptor* descriptor = [MTLTextureDescriptor
                texture2DDescriptorWithPixelFormat:MTLPixelFormatBGRA8Unorm
                width:header->width height:header->height mipmapped:NO];
            descriptor.usage = MTLTextureUsageShaderRead; descriptor.storageMode = MTLStorageModeShared;
            input = [device newTextureWithDescriptor:descriptor iosurface:surface plane:0];
            activeSurfaceID = header->surfaceID;
        }
        const uint32_t viewCount = header->viewCount;
        const uint32_t viewIndex = header->viewIndex;
        if (!input || viewCount == 0 || viewCount > QuiltColumns * QuiltRows
            || (QuiltColumns * QuiltRows) % viewCount != 0 || viewIndex >= viewCount) {
            lastSequence = sourceSequence; acknowledge(); continue;
        }
        if ((flatMode || staticMode || animatedMode) && viewCount <= 1) {
            lastSequence = sourceSequence; acknowledge(); continue;
        }
        if (flatMode && viewIndex != viewCount / 2) {
            lastSequence = sourceSequence; acknowledge(); continue;
        }
        if (!flatMode && viewIndex == 0) quiltCoverage.fill(false);
        const double cx = header->width * 0.535, cy = header->height * 0.500;
        double cropH = header->height * 0.71;
        const double cropW = std::min(double(header->width), cropH * 0.5625);
        cropH = cropW / 0.5625;
        const uint32_t cropX = uint32_t(std::clamp(cx - cropW * 0.5, 0.0, header->width - cropW));
        const uint32_t cropY = uint32_t(std::clamp(cy - cropH * 0.5, 0.0, header->height - cropH));
        ComposeParameters parameters{flatMode ? 0u : viewIndex,
            flatMode ? uint32_t(QuiltColumns * QuiltRows) : uint32_t((QuiltColumns * QuiltRows) / viewCount),
            cropX, cropY, cropX + uint32_t(cropW), cropY + uint32_t(cropH)};
        const char* renderProfile = std::getenv("GAHYEON_LOOKING_GLASS_RENDER_PROFILE");
        if (renderProfile && std::string(renderProfile) == "portrait-v001") {
            if (header->width != 252 || header->height != 448) {
                std::fprintf(stderr, "GAHYEON_LKG_PORTRAIT_SIZE_MISMATCH %ux%u\n", header->width, header->height);
                exitCode = 9; break;
            }
            // IOSurface needs a 16-byte row stride. Exclude alignment padding.
            parameters.cropMinX = parameters.cropMinY = 0;
            parameters.cropMaxX = 251;
            parameters.cropMaxY = 446;
        }
        id<MTLCommandBuffer> command = [queue commandBuffer];
        id<MTLComputeCommandEncoder> encoder = [command computeCommandEncoder];
        [encoder setComputePipelineState:pipeline];
        [encoder setTexture:input atIndex:0]; [encoder setTexture:output atIndex:1];
        [encoder setBytes:&parameters length:sizeof(parameters) atIndex:0];
        [encoder dispatchThreads:MTLSizeMake(TileWidth, TileHeight, parameters.copiesPerView)
            threadsPerThreadgroup:MTLSizeMake(16, 16, 1)];
        [encoder endEncoding]; [command commit]; [command waitUntilCompleted];
        if (!flatMode) quiltCoverage[viewIndex] = true;
        if (flatMode || viewIndex + 1 == viewCount) {
            const bool quiltComplete = flatMode || std::all_of(
                quiltCoverage.begin(), quiltCoverage.begin() + viewCount,
                [](bool captured) { return captured; });
            if (!quiltComplete) {
                std::fprintf(stderr,
                    "GAHYEON_LKG_QUILT_REJECTED reason=missing_views final_view=%u\n",
                    viewIndex);
                lastSequence = sourceSequence;
                acknowledge();
                continue;
            }
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
                std::fprintf(stderr, "GAHYEON_LKG_VIEW_BLEND center=1.0 adjacent=0.0\n");
            }
            if (smoothMode) {
                if (probeDirectory) {
                    std::vector<uint8_t> center(TileWidth * TileHeight * 4);
                    [blended getBytes:center.data() bytesPerRow:TileWidth * 4
                        fromRegion:MTLRegionMake2D(0, 3 * TileHeight, TileWidth, TileHeight) mipmapLevel:0];
                    const std::string path = std::string(probeDirectory) + "/center-"
                        + std::to_string(compressedFrames.size()) + ".rgba";
                    FILE* file = std::fopen(path.c_str(), "wb");
                    if (!file) { exitCode = 9; break; }
                    const size_t written = std::fwrite(center.data(), 1, center.size(), file);
                    const int closed = std::fclose(file);
                    if (written != center.size() || closed) { exitCode = 9; break; }
                }
                [blended getBytes:uploadBytes.data() bytesPerRow:OutputWidth * 4
                    fromRegion:MTLRegionMake2D(0, 0, OutputWidth, OutputHeight) mipmapLevel:0];
                if (!compressedFrames.append(uploadBytes.data())) {
                    std::fprintf(stderr, "GAHYEON_LKG_CACHE_FAILED bytes=%zu\n", compressedFrames.bytes());
                    exitCode = 9; break;
                }
                std::fprintf(stderr, "GAHYEON_LKG_IDLE_FRAME_READY frame=%zu/%zu cache_bytes=%zu\n",
                    compressedFrames.size(), frameCount, compressedFrames.bytes());
                if (compressedFrames.size() == frameCount) {
                    animatedCaptured = true;
                    playbackStarted = std::chrono::steady_clock::now();
                    std::fprintf(stderr, "GAHYEON_LKG_IDLE_LOOP_READY frames=%zu fps=%.1f mode=pingpong lossless=1\n",
                        compressedFrames.size(), poseFPS);
                }
            } else if (animatedMode && !flatMode) {
                void* frameRaw = nullptr;
                if (!createTexture(outputDescriptor, &frameRaw)) break;
                id<MTLTexture> frameTexture = (__bridge id<MTLTexture>)frameRaw;
                id<MTLCommandBuffer> copyCommand = [queue commandBuffer];
                id<MTLBlitCommandEncoder> copyEncoder = [copyCommand blitCommandEncoder];
                [copyEncoder copyFromTexture:blended sourceSlice:0 sourceLevel:0
                    sourceOrigin:MTLOriginMake(0, 0, 0)
                    sourceSize:MTLSizeMake(OutputWidth, OutputHeight, 1)
                    toTexture:frameTexture destinationSlice:0 destinationLevel:0
                    destinationOrigin:MTLOriginMake(0, 0, 0)];
                [copyEncoder endEncoding]; [copyCommand commit]; [copyCommand waitUntilCompleted];
                if (pacedPlayback) {
                    std::vector<uint8_t> sample(TileWidth * TileHeight * 4);
                    [frameTexture getBytes:sample.data() bytesPerRow:TileWidth * 4
                        fromRegion:MTLRegionMake2D(0, 3 * TileHeight, TileWidth, TileHeight)
                        mipmapLevel:0];
                    uint64_t checksum = 14695981039346656037ull;
                    for (uint8_t byte : sample) checksum = (checksum ^ byte) * 1099511628211ull;
                    std::fprintf(stderr, "GAHYEON_LKG_POSE_CHECKSUM frame=%zu hash=%llu\n",
                        animatedFrames.size(), static_cast<unsigned long long>(checksum));
                }
                animatedFrames.push_back(frameRaw);
                presentedTexture = frameRaw;
                std::fprintf(stderr, "GAHYEON_LKG_IDLE_FRAME_READY frame=%zu/%zu\n",
                    animatedFrames.size(), AnimatedFrameCount);
                if (animatedFrames.size() == AnimatedFrameCount) {
                    animatedCaptured = true;
                    playbackStarted = std::chrono::steady_clock::now();
                    std::fprintf(stderr,
                        "GAHYEON_LKG_IDLE_LOOP_READY frames=%zu fps=%.1f mode=pingpong\n",
                        animatedFrames.size(), poseFPS);
                }
            }
            const char* evidencePath = std::getenv("GAHYEON_LOOKING_GLASS_CENTER_RGBA");
            if (!shown && evidencePath) {
                std::vector<uint8_t> center(TileWidth * TileHeight * 4);
                [blended getBytes:center.data() bytesPerRow:TileWidth * 4
                    fromRegion:MTLRegionMake2D(0, 3 * TileHeight, TileWidth, TileHeight) mipmapLevel:0];
                FILE* file = std::fopen(evidencePath, "wb");
                if (file) { std::fwrite(center.data(), 1, center.size(), file); std::fclose(file); }
            }
            if (!presentQuilt(presentedTexture)) break;
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
        lastSequence = sourceSequence;
        acknowledge();
    }
    show_window(window, false);
    [[NSProcessInfo processInfo] endActivity:playbackActivity];
    if (surface) CFRelease(surface);
    if (header) munmap(header, 64);
    if (fd >= 0) close(fd);
    for (void* frameRaw : animatedFrames) releaseTexture(frameRaw);
    if (uploadTexture) { [glContext makeCurrentContext]; glDeleteTextures(1, &uploadTexture); }
    if (pendingDecode.valid()) pendingDecode.wait();
    releaseTexture(blendedRaw);
    releaseTexture(outputRaw); uninitialize_bridge();
    return exitCode;
}
