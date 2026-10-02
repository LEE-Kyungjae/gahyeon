import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageChops

from character_pipeline.tools.build_rgba_derivative import build_rgba_derivative, validate_matte_review


class RgbaDerivativeTest(unittest.TestCase):
    def test_rgb_is_bit_exact_and_draft_is_not_approved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source=root/"source.png"; matte=root/"matte.png"
            output=root/"out.png"; manifest=root/"manifest.json"
            Image.new("RGB", (512,512), (12,34,56)).save(source)
            alpha=Image.new("L", (512,512), 255); alpha.putpixel((0,0),0)
            proposal=Image.new("RGBA", (512,512), (200,100,50,255)); proposal.putalpha(alpha); proposal.save(matte)
            record=build_rgba_derivative(source, matte, output, manifest, 3)
            with Image.open(source) as a, Image.open(output) as b:
                self.assertIsNone(ImageChops.difference(a.convert("RGB"), b.convert("RGB")).getbbox())
            self.assertFalse(validate_matte_review(record)["approved"])
            with self.assertRaisesRegex(ValueError, "not human approved"):
                validate_matte_review(record, True)

    def test_size_mismatch_and_overwrite_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source=root/"s.png"; matte=root/"m.png"
            Image.new("RGB",(512,512)).save(source); Image.new("RGBA",(513,512)).save(matte)
            with self.assertRaisesRegex(ValueError,"dimensions"):
                build_rgba_derivative(source,matte,root/"o.png",root/"x.json",3)
            Image.new("RGBA",(512,512)).save(matte); (root/"o.png").write_bytes(b"existing")
            with self.assertRaisesRegex(ValueError,"overwrite"):
                build_rgba_derivative(source,matte,root/"o.png",root/"x.json",3)

    def test_approval_cannot_be_faked_without_reviewer(self):
        record={"status":"approved","identityAuthority":"canonical-original-rgb",
                "alphaAuthority":"ai-proposed-human-review-required","rgbInvariant":"derivative RGB equals canonical source RGB for every pixel",
                "canonicalIndex":3,"approved":True,"reviewer":None,"reviewedAt":None}
        with self.assertRaisesRegex(ValueError,"reviewer"):
            validate_matte_review(record, True)


if __name__ == "__main__": unittest.main()
