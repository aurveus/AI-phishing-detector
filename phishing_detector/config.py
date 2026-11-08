"""Settings in one place. Everything can be overridden with an environment variable."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Where the trained model lives (config.json, model.safetensors, tokenizer files).
MODEL_DIR = Path(os.environ.get("MODEL_DIR", ROOT / "models" / "phishing-detector-model"))

# Where to fetch the model from when MODEL_DIR is missing. Must be https. The download is checked against
# models/MANIFEST.sha256 before it is used, so a swapped or corrupted file is rejected.
MODEL_URL = os.environ.get(
    "MODEL_URL",
    "https://www.dropbox.com/scl/fi/cbq7qo8ki1ilzvqsp5lk2/phishing-detector-model.zip"
    "?rlkey=x613h17a4ztqxxsmlakmols65&st=5lld5pl8&dl=1",
)
MANIFEST = ROOT / "models" / "MANIFEST.sha256"
MAX_DOWNLOAD_BYTES = int(os.environ.get("MAX_DOWNLOAD_BYTES", 600 * 1024 * 1024))
DOWNLOAD_TIMEOUT_S = 30

# Training data (not in git; see data/README.md).
DATA_CSV = Path(os.environ.get("DATA_CSV", ROOT / "data" / "Phishing_Email.csv"))

LABELS = {0: "Safe Email", 1: "Phishing Email"}

# The model was trained on text cut to 128 tokens, so inference uses the same length.
MAX_TOKENS = 128
# Reject absurd inputs early (the dataset contains one 15-million-character "email").
MAX_INPUT_CHARS = int(os.environ.get("MAX_INPUT_CHARS", 20_000))

SEED = 42
