import unittest
from pathlib import Path
from character_pipeline.tools.verify_facial_actuation_runner_scaffold import verify
class T(unittest.TestCase):
 def test_current_scaffold(self):
  v=verify(Path.cwd());self.assertTrue(v["asymmetricBlink"]);self.assertEqual(v["samples"],57);self.assertEqual(v["controlRigExecution"],"typed-bridge-required")
if __name__=="__main__":unittest.main()
