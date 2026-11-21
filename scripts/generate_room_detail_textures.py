"""Generate deterministic, original room surface textures without external assets."""
from pathlib import Path
import math
import random
import struct
import zlib


def generate(destination: Path, fine_grain: bool = False):
    destination.mkdir(parents=True, exist_ok=True)
    size = 256
    for kind in ('oak', 'plaster', 'linen', 'sky'):
        rng = random.Random(12012)
        data = bytearray()
        for y in range(size):
            data.append(0)
            for x in range(size):
                noise = rng.uniform(-1, 1)
                if kind == 'oak':
                    grain = math.sin(x * .045 + math.sin(y * .026) * .3)
                    fine = math.sin(x * .18 + math.sin(y * .02))
                    value = grain * 4 + fine * 1.5 + noise * 1.5
                    if fine_grain:
                        grain = math.sin(x * .32 + math.sin(y * .026) * 1.2)
                        fine = math.sin(x * 1.8 + math.sin(y * .02))
                        value = grain * 9 + fine * 3 + noise * 3
                    rgb = (145 + value, 111 + value * .8, 76 + value * .6)
                elif kind == 'plaster':
                    value = noise * 3
                    rgb = (196 + value, 188 + value, 169 + value)
                elif kind == 'linen':
                    value = (x % 3 == 0) * -9 + (y % 3 == 0) * -6 + noise * 2
                    rgb = (212 + value, 202 + value, 177 + value)
                else:
                    t = y / (size - 1)
                    rgb = (104 + t * 99, 146 + t * 61, 180 + t * 20)
                data.extend(max(0, min(255, round(v))) for v in rgb)
        def chunk(tag, payload):
            return struct.pack('>I', len(payload)) + tag + payload + struct.pack('>I', zlib.crc32(tag + payload))
        png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0))
        png += chunk(b'IDAT', zlib.compress(data)) + chunk(b'IEND', b'')
        (destination / (kind + '.png')).write_bytes(png)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    generate(parser.parse_args().destination)
