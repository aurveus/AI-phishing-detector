# Models

The trained model (about 257 MB) is not stored in git. `models/phishing-detector-model/` is created automatically the
first time the app starts: it is downloaded, every file is checked against `MANIFEST.sha256`, and only then used.

To train your own instead: `python -m phishing_detector.train` (see the main README), then
`python -m phishing_detector.model_store manifest` to record its checksums.
