import json, tempfile, unittest
from pathlib import Path
from PIL import Image, ImageChops
from character_pipeline.tools.matte_correction import apply_matte_corrections, digest

CONFIG=json.loads(Path("character_pipeline/config/matte_correction.json").read_text())

class MatteCorrectionTest(unittest.TestCase):
    def fixture(self, root):
        src=root/"src.png"; layer=root/"layer.png"; out=root/"out.png"; manifest=root/"out.json"
        Image.new("RGBA",(1254,1254),(10,20,30,0)).save(src)
        mask=Image.new("L",(1254,1254),0); mask.rectangle if False else None
        for x in range(200,210):
            for y in range(100,110): mask.putpixel((x,y),255)
        mask.save(layer)
        correction={"canonicalIndex":3,"layers":[{"operation":"add","roi":"hair-top","path":str(layer.resolve()),"sha256":digest(layer)}]}
        return src,layer,out,manifest,correction
    def test_add_layer_preserves_rgb_and_stays_draft(self):
        with tempfile.TemporaryDirectory() as d:
            src,layer,out,manifest,c=self.fixture(Path(d)); record=apply_matte_corrections(CONFIG,src,c,out,manifest)
            with Image.open(src) as a, Image.open(out) as b: self.assertIsNone(ImageChops.difference(a.convert("RGB"),b.convert("RGB")).getbbox())
            self.assertFalse(record["approved"]); self.assertEqual(record["layers"][0]["operation"],"add")
    def test_checksum_and_roi_escape_fail(self):
        with tempfile.TemporaryDirectory() as d:
            src,layer,out,manifest,c=self.fixture(Path(d)); c["layers"][0]["sha256"]="0"*64
            with self.assertRaisesRegex(ValueError,"checksum"): apply_matte_corrections(CONFIG,src,c,out,manifest)
            c["layers"][0]["sha256"]=digest(layer); im=Image.open(layer); im.putpixel((1200,1200),255); im.save(layer); c["layers"][0]["sha256"]=digest(layer)
            with self.assertRaisesRegex(ValueError,"escapes"): apply_matte_corrections(CONFIG,src,c,out,manifest)
    def test_overwrite_fails(self):
        with tempfile.TemporaryDirectory() as d:
            src,layer,out,manifest,c=self.fixture(Path(d)); out.write_bytes(b"x")
            with self.assertRaisesRegex(ValueError,"overwrite"): apply_matte_corrections(CONFIG,src,c,out,manifest)
    def test_remove_and_replace_have_explicit_semantics(self):
        for operation, expected in (("remove",0),("replace",255)):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as d:
                src,layer,out,manifest,c=self.fixture(Path(d)); base=Image.new("RGBA",(1254,1254),(10,20,30,255)); base.save(src)
                c["layers"][0]["operation"]=operation
                apply_matte_corrections(CONFIG,src,c,out,manifest)
                self.assertEqual(Image.open(out).getchannel("A").getpixel((205,105)),expected)

if __name__=="__main__": unittest.main()
