#import <CoreGraphics/CoreGraphics.h>
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>

#include "bridge.h"

#include <algorithm>
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
constexpr uint32_t FrameMagic = 0x47485247;
constexpr size_t HeaderBytes = 64;
constexpr size_t QuiltColumns = 11;
constexpr size_t QuiltRows = 6;
constexpr size_t TileWidth = 372;
constexpr size_t TileHeight = 682;
constexpr size_t OutputWidth = QuiltColumns * TileWidth;
constexpr size_t OutputHeight = QuiltRows * TileHeight;
std::atomic<bool> Running{true};

struct FrameHeader {
    uint32_t magic, version, width, height, stride, activeBuffer;
    uint64_t sequence;
    uint32_t alphaMin, alphaMax, boundsMinX, boundsMinY, boundsMaxX, boundsMaxY;
    uint32_t viewIndex, viewCount;
};
static_assert(sizeof(FrameHeader) == HeaderBytes);

void Stop(int) { Running.store(false); }

}

int main() {
    signal(SIGINT, Stop); signal(SIGTERM, Stop);
    id<MTLDevice> metalDevice = MTLCreateSystemDefaultDevice();
    if (!metalDevice || !initialize_bridge("Gahyeon Looking Glass")) {
        std::fprintf(stderr, "GAHYEON_LKG_METAL_INIT_FAILED\n");
        return 4;
    }
    WINDOW_HANDLE window = 0;
    if (!instance_window_metal((__bridge void*)metalDevice, &window, FIRST_LOOKING_GLASS_DEVICE)) {
        std::fprintf(stderr, "GAHYEON_LKG_METAL_WINDOW_FAILED\n");
        uninitialize_bridge();
        return 5;
    }
    unsigned long displayIndex = 0;
    get_display_for_window(window, &displayIndex);
    MTLTextureDescriptor* descriptor = [MTLTextureDescriptor
        texture2DDescriptorWithPixelFormat:MTLPixelFormatRGBA8Unorm
        width:OutputWidth height:OutputHeight mipmapped:NO];
    descriptor.usage = MTLTextureUsageShaderRead;
    descriptor.storageMode = MTLStorageModeShared;
    void* bridgeTextureRaw = nullptr;
    if (!create_metal_texture_with_iosurface(window, (__bridge void*)descriptor, &bridgeTextureRaw)) {
        std::fprintf(stderr, "GAHYEON_LKG_METAL_TEXTURE_FAILED\n");
        uninitialize_bridge();
        return 6;
    }
    id<MTLTexture> bridgeTexture = (__bridge id<MTLTexture>)bridgeTextureRaw;
    show_window(window, true);
    std::fprintf(stderr, "GAHYEON_LKG_METAL_READY display=%lu quilt=%zux%zu views=%zux%zu\n",
                 displayIndex, OutputWidth, OutputHeight, QuiltColumns, QuiltRows);
    int fd = -1;
    while (Running.load() && fd < 0) {
        fd = shm_open("/gahyeon_rgba_v003", O_RDONLY, 0);
        if (fd < 0) std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    struct stat info {};
    if (fd < 0 || fstat(fd, &info) != 0) return 2;
    const size_t regionBytes = static_cast<size_t>(info.st_size);
    auto* region = static_cast<uint8_t*>(mmap(nullptr, regionBytes, PROT_READ, MAP_SHARED, fd, 0));
    if (region == MAP_FAILED) return 3;

    uint64_t lastSequence = 0;
    auto nextFrame = std::chrono::steady_clock::now();
    CGColorSpaceRef colorSpace = CGColorSpaceCreateDeviceRGB();
    const size_t outputStride = OutputWidth * 4;
    auto* outputPixels = static_cast<uint8_t*>(std::calloc(OutputHeight, outputStride));
    CGContextRef context = CGBitmapContextCreate(
        outputPixels, OutputWidth, OutputHeight, 8, outputStride, colorSpace,
        kCGBitmapByteOrder32Little | kCGImageAlphaPremultipliedFirst);
    CGContextSetRGBFillColor(context, 0, 0, 0, 1);
    CGContextFillRect(context, CGRectMake(0, 0, OutputWidth, OutputHeight));
    CGContextSetInterpolationQuality(context, kCGInterpolationHigh);
    CGContextTranslateCTM(context, 0, OutputHeight);
    CGContextScaleCTM(context, 1, -1);
    while (Running.load()) @autoreleasepool {
        const auto* header = reinterpret_cast<const FrameHeader*>(region);
        if (header->magic != FrameMagic || header->sequence == 0 || header->sequence == lastSequence ||
            std::chrono::steady_clock::now() < nextFrame) {
            std::this_thread::sleep_for(std::chrono::milliseconds(2));
            continue;
        }
        const size_t frameBytes = static_cast<size_t>(header->stride) * header->height;
        const size_t offset = HeaderBytes + static_cast<size_t>(header->activeBuffer) * frameBytes;
        if (header->stride != header->width * 4 || offset + frameBytes > regionBytes) break;

        CFDataRef pixels = CFDataCreate(kCFAllocatorDefault, region + offset, frameBytes);
        CGDataProviderRef provider = CGDataProviderCreateWithCFData(pixels);
        CGImageRef sourceImage = CGImageCreate(
            header->width, header->height, 8, 32, header->stride, colorSpace,
            kCGBitmapByteOrder32Little | kCGImageAlphaPremultipliedFirst,
            provider, nullptr, true, kCGRenderingIntentDefault);
        const uint32_t left = header->boundsMinX > 80 ? header->boundsMinX - 80 : 0;
        const uint32_t top = header->boundsMinY > 50 ? header->boundsMinY - 50 : 0;
        const uint32_t right = std::min(header->width, header->boundsMaxX + 81);
        const uint32_t bottom = std::min(header->height, header->boundsMaxY + 51);
        const CGRect cropRect = CGRectMake(left, top, std::max(1u, right - left),
                                           std::max(1u, bottom - top));
        CGImageRef croppedImage = CGImageCreateWithImageInRect(sourceImage, cropRect);
        const CGFloat scale = std::min(
            CGFloat(TileWidth) / CGFloat(CGImageGetWidth(croppedImage)),
            CGFloat(TileHeight) / CGFloat(CGImageGetHeight(croppedImage)));
        const CGSize fitted = CGSizeMake(CGImageGetWidth(croppedImage) * scale,
                                         CGImageGetHeight(croppedImage) * scale);
        if (header->viewCount == QuiltColumns * QuiltRows) {
            if (header->viewIndex == 0) {
                CGContextSetRGBFillColor(context, 0, 0, 0, 1);
                CGContextFillRect(context, CGRectMake(0, 0, OutputWidth, OutputHeight));
            }
            const size_t row = header->viewIndex / QuiltColumns;
            const size_t column = header->viewIndex % QuiltColumns;
            if (row < QuiltRows) {
                const CGRect destinationRect = CGRectMake(
                    column * TileWidth + (TileWidth - fitted.width) * 0.5,
                    row * TileHeight + (TileHeight - fitted.height) * 0.5,
                    fitted.width, fitted.height);
                CGContextDrawImage(context, destinationRect, croppedImage);
            }
        } else {
            for (size_t row = 0; row < QuiltRows; ++row) {
                for (size_t column = 0; column < QuiltColumns; ++column) {
                    const CGRect destinationRect = CGRectMake(
                        column * TileWidth + (TileWidth - fitted.width) * 0.5,
                        row * TileHeight + (TileHeight - fitted.height) * 0.5,
                        fitted.width, fitted.height);
                    CGContextDrawImage(context, destinationRect, croppedImage);
                }
            }
        }
        const bool quiltComplete = header->viewCount != QuiltColumns * QuiltRows
            || header->viewIndex == QuiltColumns * QuiltRows - 1;
        bool presented = true;
        if (quiltComplete) {
            for (size_t pixel = 0; pixel < OutputWidth * OutputHeight; ++pixel) {
                std::swap(outputPixels[pixel * 4], outputPixels[pixel * 4 + 2]);
            }
            const MTLRegion textureRegion = MTLRegionMake2D(0, 0, OutputWidth, OutputHeight);
            [bridgeTexture replaceRegion:textureRegion mipmapLevel:0
                              withBytes:outputPixels bytesPerRow:outputStride];
            presented = draw_interop_quilt_texture_metal(
                window, bridgeTextureRaw, QuiltColumns, QuiltRows, 0.5625f, 1.0f);
            if (!presented) std::fprintf(stderr, "GAHYEON_LKG_METAL_DRAW_FAILED\n");
            for (size_t pixel = 0; pixel < OutputWidth * OutputHeight; ++pixel) {
                std::swap(outputPixels[pixel * 4], outputPixels[pixel * 4 + 2]);
            }
        }

        CGImageRelease(croppedImage);
        CGImageRelease(sourceImage);
        CGDataProviderRelease(provider); CFRelease(pixels);
        if (!presented) break;
        lastSequence = header->sequence;
        nextFrame = std::chrono::steady_clock::now() + std::chrono::milliseconds(10);
    }
    show_window(window, false);
    release_metal_texture(window, bridgeTextureRaw);
    uninitialize_bridge();
    CGContextRelease(context); std::free(outputPixels); CGColorSpaceRelease(colorSpace);
    munmap(region, regionBytes); close(fd);
    return 0;
}
