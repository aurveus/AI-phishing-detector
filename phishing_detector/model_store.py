"""Fetch the trained model safely.

Steps: https only, timeout, size cap, extract into a temporary folder with a path check (no zip-slip), verify every
file against models/MANIFEST.sha256, only then move it into place.

  python -m phishing_detector.model_store manifest   # (re)write the manifest from the local model folder
  python -m phishing_detector.model_store verify     # check the local model folder against the manifest
"""
import hashlib
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlparse

from . import config

REQUIRED_FILES = ("config.json", "model.safetensors", "tokenizer.json", "tokenizer_config.json", "vocab.txt")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_manifest(path: Path = config.MANIFEST) -> dict:
    entries = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            digest, name = line.split(None, 1)
            entries[name.strip().lstrip("*")] = digest
    return entries


def write_manifest(model_dir: Path = config.MODEL_DIR, path: Path = config.MANIFEST) -> None:
    lines = ["# SHA-256 of every file the model needs. Checked after download (phishing_detector/model_store.py)."]
    for p in sorted(model_dir.iterdir()):
        if p.is_file():
            lines.append(f"{sha256_file(p)}  {p.name}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify(model_dir: Path, manifest: Path = config.MANIFEST) -> None:
    """Raise ValueError if a required file is missing or does not match the manifest."""
    expected = read_manifest(manifest)
    for name in REQUIRED_FILES:
        if name not in expected:
            raise ValueError(f"{name} is not listed in the manifest")
        f = model_dir / name
        if not f.is_file():
            raise ValueError(f"model file missing: {name}")
        if sha256_file(f) != expected[name]:
            raise ValueError(f"checksum mismatch for {name}: refusing to use this model")


def safe_extract(zip_path: Path, dest: Path) -> None:
    """Extract, refusing any entry that would land outside dest (zip-slip) and absurd total sizes."""
    dest = dest.resolve()
    with zipfile.ZipFile(zip_path) as z:
        total = 0
        for info in z.infolist():
            target = (dest / info.filename).resolve()
            if dest != target and dest not in target.parents:
                raise ValueError(f"unsafe path in archive: {info.filename}")
            total += info.file_size
            if total > config.MAX_DOWNLOAD_BYTES * 2:
                raise ValueError("archive expands to an unreasonable size")
        z.extractall(dest)


def install_from_zip(zip_path: Path, model_dir: Path = config.MODEL_DIR, manifest: Path = config.MANIFEST) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        safe_extract(zip_path, tmp_dir)
        entries = list(tmp_dir.iterdir())
        root = entries[0] if len(entries) == 1 and entries[0].is_dir() else tmp_dir  # zip may have one top folder
        verify(root, manifest)
        if model_dir.exists():
            shutil.rmtree(model_dir)
        model_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(root), str(model_dir))


def download(url: str, dest: Path) -> None:
    import requests  # imported here so the checks above work without it

    if urlparse(url).scheme != "https":
        raise ValueError("MODEL_URL must be an https URL")
    with requests.get(url, stream=True, timeout=config.DOWNLOAD_TIMEOUT_S) as r:
        r.raise_for_status()
        size = 0
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                size += len(chunk)
                if size > config.MAX_DOWNLOAD_BYTES:
                    raise ValueError("download is larger than MAX_DOWNLOAD_BYTES: aborting")
                f.write(chunk)


def ensure_model(model_dir: Path = config.MODEL_DIR) -> Path:
    """Return the model folder, downloading and verifying it first if it is not there."""
    if (model_dir / "model.safetensors").is_file():
        return model_dir
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / "model.zip"
        download(config.MODEL_URL, zip_path)
        install_from_zip(zip_path, model_dir)
    return model_dir


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "manifest":
        write_manifest()
        print("wrote", config.MANIFEST)
    elif cmd == "verify":
        verify(config.MODEL_DIR)
        print("model files match the manifest")
    else:
        sys.exit(__doc__)
