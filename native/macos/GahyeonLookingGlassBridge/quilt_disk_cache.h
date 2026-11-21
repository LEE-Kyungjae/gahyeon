#pragma once
#include <compression.h>
#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>
#include <filesystem>

// LZ4 is chosen for bounded decode latency. Disk storage avoids retaining every
// room quilt in unified memory alongside Unreal and the display compositor.
class QuiltDiskCache {
public:
    QuiltDiskCache(size_t frameBytes, size_t budgetBytes, const std::string& directory)
        : frameBytes_(frameBytes), budgetBytes_(budgetBytes), directory_(directory) {
        std::filesystem::create_directories(directory_);
        packed_.resize(frameBytes_ + 65536);
        for (size_t i=0;;++i) {
            auto p = path(i);
            if (!std::filesystem::exists(p)) break;
            size_t n = std::filesystem::file_size(p);
            if (!n || n > packed_.size() || n > budgetBytes_-usedBytes_) break;
            sizes_.push_back(n); usedBytes_ += n;
        }
    }
    bool append(const uint8_t* bytes) {
        if (!retained_.empty()) return false;
        size_t n = compression_encode_buffer(packed_.data(), packed_.size(), bytes,
            frameBytes_, nullptr, COMPRESSION_LZ4);
        if (!n || n > budgetBytes_-usedBytes_) return false;
        std::string tmp = path(size()) + ".tmp";
        FILE* f = std::fopen(tmp.c_str(), "wb");
        if (!f) return false;
        bool ok = std::fwrite(packed_.data(),1,n,f)==n;
        ok = std::fclose(f)==0 && ok;
        if (!ok || std::rename(tmp.c_str(),path(size()).c_str())) return false;
        sizes_.push_back(n); usedBytes_ += n;
        return true;
    }
    bool decode(size_t index, uint8_t* bytes) {
        if (index >= size()) return false;
        const bool retained = !retained_.empty() && !retained_[index].empty();
        auto& packed = retained_.empty() ? packed_ : retained_[index];
        if (!retained) {
            if (packed.size() < sizes_[index]) packed.resize(sizes_[index]);
            FILE* f = std::fopen(path(index).c_str(), "rb");
            if (!f) { if (!retained_.empty()) packed.clear(); return false; }
            const bool ok = std::fread(packed.data(),1,sizes_[index],f)==sizes_[index];
            std::fclose(f);
            if (!ok) { if (!retained_.empty()) packed.clear(); return false; }
        }
        return compression_decode_buffer(bytes,frameBytes_,packed.data(),
            sizes_[index],nullptr,COMPRESSION_LZ4)==frameBytes_;
    }
    // Admit the complete compressed loop only if it fits the explicit RAM cap.
    // Fill lazily while decoding; never keep uncompressed quilts in memory.
    bool retainCompressed(size_t expected, size_t memoryBudgetBytes) {
        if (size() != expected || usedBytes_ > memoryBudgetBytes) return false;
        retained_.resize(size());
        return true;
    }
    void discardIncomplete(size_t expected) {
        if (size()==expected) return;
        for(size_t i=0;i<size();++i) std::filesystem::remove(path(i));
        sizes_.clear(); retained_.clear(); usedBytes_=0;
    }
    size_t size() const { return sizes_.size(); }
    size_t bytes() const { return usedBytes_; }
private:
    std::string path(size_t i) const { return directory_+"/pose-"+std::to_string(i)+".lz4"; }
    size_t frameBytes_, budgetBytes_, usedBytes_=0;
    std::string directory_;
    std::vector<size_t> sizes_;
    std::vector<std::vector<uint8_t>> retained_;
    std::vector<uint8_t> packed_;
};
