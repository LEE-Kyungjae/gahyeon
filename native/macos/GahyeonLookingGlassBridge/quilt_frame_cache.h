#pragma once
#include <compression.h>
#include <cstdint>
#include <vector>

// Lossless, bounded cache: retain compressed quilts instead of one GPU texture per pose.
class QuiltFrameCache {
public:
    explicit QuiltFrameCache(size_t frameBytes, size_t budgetBytes)
        : frameBytes_(frameBytes), budgetBytes_(budgetBytes) {}

    bool append(const uint8_t* bytes) {
        std::vector<uint8_t> packed(frameBytes_ + 65536);
        const size_t count = compression_encode_buffer(packed.data(), packed.size(),
            bytes, frameBytes_, nullptr, COMPRESSION_LZFSE);
        if (!count || count > budgetBytes_ - usedBytes_) return false;
        // Copy to exact-size storage so vector capacity cannot retain the raw allocation.
        frames_.emplace_back(packed.begin(), packed.begin() + count);
        usedBytes_ += count;
        return true;
    }

    bool decode(size_t index, uint8_t* bytes) const {
        if (index >= frames_.size()) return false;
        const auto& packed = frames_[index];
        return compression_decode_buffer(bytes, frameBytes_, packed.data(), packed.size(),
            nullptr, COMPRESSION_LZFSE) == frameBytes_;
    }

    size_t size() const { return frames_.size(); }
    size_t bytes() const { return usedBytes_; }

private:
    size_t frameBytes_, budgetBytes_, usedBytes_ = 0;
    std::vector<std::vector<uint8_t>> frames_;
};
