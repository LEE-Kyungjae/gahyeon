"""Exercise the native lossless cache, including rejection without state corruption."""
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


@unittest.skipUnless(sys.platform == "darwin", "Apple Compression framework")
class QuiltFrameCacheTest(unittest.TestCase):
    def test_roundtrip_and_memory_budget(self):
        source = r'''
#include "quilt_frame_cache.h"
#include <cassert>
#include <random>
int main() {
    constexpr size_t size = 256 * 1024;
    std::vector<uint8_t> blank(size, 0), noise(size), output(size);
    std::mt19937 random(123);
    for (auto& byte : noise) byte = uint8_t(random());
    QuiltFrameCache cache(size, size * 3);
    assert(cache.append(blank.data()));
    assert(cache.append(noise.data()));
    assert(cache.size() == 2);
    assert(cache.decode(0, output.data()) && output == blank);
    assert(cache.decode(1, output.data()) && output == noise);
    assert(!cache.decode(2, output.data()));
    QuiltFrameCache bounded(size, 8192);
    assert(bounded.append(blank.data()));
    const size_t before = bounded.bytes();
    assert(!bounded.append(noise.data()));
    assert(bounded.size() == 1 && bounded.bytes() == before);
    assert(bounded.decode(0, output.data()) && output == blank);
    assert(bounded.append(blank.data()));
}
'''
        with tempfile.TemporaryDirectory() as directory:
            cpp = pathlib.Path(directory) / "test.cpp"
            binary = pathlib.Path(directory) / "test"
            cpp.write_text(source)
            subprocess.run([
                "clang++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                "-I", str(ROOT / "native/macos/GahyeonLookingGlassBridge"),
                str(cpp), "-lcompression", "-o", str(binary),
            ], check=True, capture_output=True)
            subprocess.run([str(binary)], check=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()
