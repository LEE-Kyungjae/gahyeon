import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class DiskCacheTests(unittest.TestCase):
    def test_roundtrip_restart_budget_and_partial_capture(self):
        source = r'''
#include "quilt_disk_cache.h"
#include <cassert>
#include <random>
int main(int, char** argv) {
    constexpr size_t n=256*1024;
    std::vector<uint8_t> zero(n,0), noise(n), out(n);
    std::mt19937 random(123);
    for(auto& b:noise) b=uint8_t(random());
    std::string dir=argv[1];
    {
        QuiltDiskCache c(n, n*4, dir);
        assert(c.append(zero.data()) && c.append(noise.data()));
        assert(c.decode(1,out.data()) && out==noise);
        assert(!c.decode(2,out.data()));
    }
    QuiltDiskCache restored(n,n*4,dir);
    restored.discardIncomplete(2);
    assert(restored.size()==2 && restored.decode(0,out.data()) && out==zero);
    restored.discardIncomplete(3);
    assert(restored.size()==0 && restored.bytes()==0);
    assert(!std::filesystem::exists(dir+"/pose-0.lz4"));
    QuiltDiskCache bounded(n,8192,dir+"/bounded");
    assert(bounded.append(zero.data()));
    size_t before=bounded.bytes();
    assert(!bounded.append(noise.data()) && bounded.bytes()==before && bounded.size()==1);
    assert(bounded.decode(0,out.data()) && out==zero);
    assert(!bounded.retainCompressed(2,8192));
    assert(!bounded.retainCompressed(1,1));
    assert(bounded.retainCompressed(1,8192));
    assert(bounded.decode(0,out.data()) && out==zero);
    assert(!bounded.append(zero.data()));
    std::filesystem::remove(dir+"/bounded/pose-0.lz4");
    assert(bounded.decode(0,out.data()) && out==zero); // no disk dependency after first read
    bounded.discardIncomplete(2);
    assert(bounded.size()==0 && bounded.append(zero.data()));
}
'''
        with tempfile.TemporaryDirectory() as directory:
            d=pathlib.Path(directory)
            (d/'test.cpp').write_text(source)
            subprocess.run(['clang++','-std=c++17','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/macos/GahyeonLookingGlassBridge'),str(d/'test.cpp'),'-lcompression','-o',str(d/'test')],check=True)
            subprocess.run([str(d/'test'),str(d/'cache')],check=True)

if __name__ == '__main__':
    unittest.main()
