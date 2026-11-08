"""Clicks through the real Streamlit app. Needs the model folder (skipped if it is not downloaded yet)."""
import unittest
from pathlib import Path

from phishing_detector import config

try:
    from streamlit.testing.v1 import AppTest
except ImportError:  # streamlit too old for the test helper
    AppTest = None

APP = str(Path(__file__).resolve().parent.parent / "app.py")
HAVE_MODEL = (config.MODEL_DIR / "model.safetensors").is_file()


@unittest.skipUnless(AppTest and HAVE_MODEL, "needs streamlit's AppTest and the downloaded model")
class AppFlowTests(unittest.TestCase):
    def fresh(self):
        at = AppTest.from_file(APP, default_timeout=180).run()
        self.assertFalse(at.exception, at.exception)
        return at

    def test_phishing_example_is_flagged(self):
        at = self.fresh()
        at.button(key="ex_phish").click().run()
        self.assertFalse(at.exception, at.exception)
        page = " ".join(m.value for m in at.markdown)
        self.assertIn("Likely phishing", page)
        self.assertIn("hxxp://", " ".join(c.value for c in at.code))  # link shown defanged

    def test_safe_example_passes(self):
        at = self.fresh()
        at.button(key="ex_safe").click().run()
        self.assertIn("Looks safe", " ".join(m.value for m in at.markdown))

    def test_empty_input_warns_and_clear_works(self):
        at = self.fresh()
        at.button(key="detect").click().run()
        self.assertTrue(at.warning)
        at.button(key="ex_safe").click().run()
        at.button(key="clear").click().run()
        self.assertEqual(at.text_area(key="email_text").value, "")


if __name__ == "__main__":
    unittest.main()
