"""Run: python -m unittest discover -s tests -v   (no model, data or GPU needed)"""
import tempfile
import unittest
import zipfile
from pathlib import Path

from phishing_detector import model_store
from phishing_detector.preprocess import clean_text
from phishing_detector.signals import defang, find_signals


class CleanTextTests(unittest.TestCase):
    def test_links_and_addresses_become_words(self):
        self.assertEqual(clean_text("Visit http://evil.example/x?a=1 or mail bob@corp.com now"), "visit url or mail email now")

    def test_lowercases_and_drops_digits_and_symbols(self):
        self.assertEqual(clean_text("URGENT!!! Verify 123 account $$$"), "urgent verify  account ")


class ModelStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.model = self.tmp / "model"
        self.model.mkdir()
        for name in model_store.REQUIRED_FILES:
            (self.model / name).write_text(f"content of {name}")
        self.manifest = self.tmp / "MANIFEST.sha256"
        model_store.write_manifest(self.model, self.manifest)

    def make_zip(self, mutate=None, evil=False):
        z = self.tmp / "m.zip"
        with zipfile.ZipFile(z, "w") as zf:
            for name in model_store.REQUIRED_FILES:
                data = "tampered" if name == mutate else (self.model / name).read_text()
                zf.writestr(name, data)
            if evil:
                zf.writestr("../escaped.txt", "x")
        return z

    def test_good_archive_installs(self):
        dest = self.tmp / "installed"
        model_store.install_from_zip(self.make_zip(), dest, self.manifest)
        self.assertTrue((dest / "model.safetensors").is_file())

    def test_tampered_file_is_rejected(self):
        with self.assertRaises(ValueError):
            model_store.install_from_zip(self.make_zip(mutate="model.safetensors"), self.tmp / "x", self.manifest)
        self.assertFalse((self.tmp / "x").exists())

    def test_zip_slip_is_rejected(self):
        with self.assertRaises(ValueError):
            model_store.install_from_zip(self.make_zip(evil=True), self.tmp / "y", self.manifest)
        self.assertFalse((self.tmp / "escaped.txt").exists())

    def test_http_url_is_refused(self):
        with self.assertRaises(ValueError):
            model_store.download("http://example.com/m.zip", self.tmp / "m.zip")


class SignalTests(unittest.TestCase):
    def test_defang_makes_links_inert(self):
        self.assertEqual(defang("http://evil.example.com/x"), "hxxp://evil[.]example[.]com/x")

    def test_obvious_phish_triggers_several_signals(self):
        s = " ".join(find_signals("URGENT! Verify your account password at http://192.168.4.4/login or https://bit.ly/x"))
        for needle in ("link", "IP address", "shortener", "encrypted", "urgent", "sensitive"):
            self.assertIn(needle, s)

    def test_plain_email_has_no_signals(self):
        self.assertEqual(find_signals("Hi team, the agenda for Thursday is attached. Thanks, Sam"), [])


if __name__ == "__main__":
    unittest.main()
