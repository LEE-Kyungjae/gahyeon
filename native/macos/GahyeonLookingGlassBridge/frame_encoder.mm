#import <CoreGraphics/CoreGraphics.h>
#import <Foundation/Foundation.h>
#import <ImageIO/ImageIO.h>

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

bool WriteAll(const void* source, size_t bytes) {
    const auto* cursor = static_cast<const uint8_t*>(source);
    while (bytes > 0) {
        const ssize_t written = write(STDOUT_FILENO, cursor, bytes);
        if (written <= 0) return false;
        cursor += written;
        bytes -= static_cast<size_t>(written);
    }
    return true;
}
}

int main() {
    signal(SIGINT, Stop); signal(SIGTERM, Stop); signal(SIGPIPE, Stop);
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
        CGImageRef image = quiltComplete ? CGBitmapContextCreateImage(context) : nullptr;
        CFMutableDataRef encoded = CFDataCreateMutable(kCFAllocatorDefault, 0);
        CGImageDestinationRef destination = image ? CGImageDestinationCreateWithData(
            encoded, CFSTR("public.jpeg"), 1, nullptr) : nullptr;
        const void* keys[] = { kCGImageDestinationLossyCompressionQuality };
        const void* values[] = { (__bridge CFNumberRef)@(0.82) };
        CFDictionaryRef options = CFDictionaryCreate(
            kCFAllocatorDefault, keys, values, 1,
            &kCFTypeDictionaryKeyCallBacks, &kCFTypeDictionaryValueCallBacks);
        if (destination) CGImageDestinationAddImage(destination, image, options);
        const bool finalized = destination && CGImageDestinationFinalize(destination);
        const uint32_t length = finalized ? static_cast<uint32_t>(CFDataGetLength(encoded)) : 0;
        const uint32_t networkLength = __builtin_bswap32(length);
        const bool written = length > 0 && WriteAll(&networkLength, sizeof(networkLength)) &&
            WriteAll(CFDataGetBytePtr(encoded), length);

        CFRelease(options); if (destination) CFRelease(destination); CFRelease(encoded);
        if (image) CGImageRelease(image); CGImageRelease(croppedImage);
        CGImageRelease(sourceImage);
        CGDataProviderRelease(provider); CFRelease(pixels);
        if (quiltComplete && !written) break;
        lastSequence = header->sequence;
        nextFrame = std::chrono::steady_clock::now() + std::chrono::milliseconds(10);
    }
    CGContextRelease(context); std::free(outputPixels); CGColorSpaceRelease(colorSpace);
    munmap(region, regionBytes); close(fd);
    return 0;
}
