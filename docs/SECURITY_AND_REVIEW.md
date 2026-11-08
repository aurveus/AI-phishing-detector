# Security and code review

Scope: the whole repository (code, dependencies, git history) and how the app handles input. Method: manual code review, `pip-audit` on the dependency versions, a search of the full git history for secrets, and running the app, tests and evaluation.

## Findings

| # | Severity | Finding | Status |
|---|---|---|---|
| 1 | High | **Known-vulnerable dependencies.** The pinned versions (`torch 2.5.1`, `transformers 4.33.2`, `streamlit 1.24.1`) had **81 known vulnerabilities** reported by `pip-audit`. The pins also did not match what was actually installed and working (`transformers 4.54`, `streamlit 1.47`), and `eval_strategy` in the training script does not exist in `transformers 4.33`, so the pinned file could not run the training script. | **Fixed.** `requirements.txt` now sets lower bounds at fixed versions. A clean install resolved to current releases (streamlit 1.67, torch 2.15, transformers 5.22); the app and tests pass on them and `pip-audit` reports nothing for the project's packages. |
| 2 | Medium | **Unverified model download.** The app downloaded a zip from a hardcoded Dropbox link with no timeout, no HTTP status check, no size limit and no integrity check, then `extractall`'d it. A swapped or corrupted file would have been loaded silently. | **Fixed.** https only, timeout, size cap, extraction into a temp folder with a path-escape (zip-slip) check, every file checked against `models/MANIFEST.sha256`, then moved into place. Unit-tested, including a tampered file and a malicious archive. |
| 3 | Medium | **No input limits.** The text box accepted unlimited text; the dataset itself contains a 15-million-character "email", showing how large inputs occur. On a public deployment this is a cheap way to exhaust memory or CPU. | **Fixed.** 20,000-character cap on the text box and in code, tokens cut at 128, inference under `torch.no_grad()`, model loaded once and cached instead of on every page interaction. |
| 4 | Medium | **Training/inference mismatch.** Training cleaned the text (lowercase, links to "url", addresses to "email", letters only); the app sent the model raw text. | **Fixed** with one shared `clean_text`. Effect measured: raw input missed 45 phishing emails in the test split instead of 29 (recall 97.0% vs 98.1%). |
| 5 | Medium | **Evaluation method.** The original run used the test set as its validation set to choose the best epoch, and 384 of the 3,727 test emails (10%) also appear in the training data. Reported accuracy can therefore be optimistic. | **Measured and documented; published model not retrained.** On the 3,343 test emails not seen in training, accuracy is 98.3% (higher, not lower), so the headline holds. `train.py` now removes duplicates and uses separate validation and test sets for future runs. |
| 6 | Low | **Download link in source and history.** The Dropbox share link (including its `rlkey` access key) is in the code and one commit. It points at a public model, so this is not a credential leak, but the key cannot be rotated out of history. | **Mitigated.** Moved to `config.py` and overridable with `MODEL_URL`; the checksum check protects integrity. Recommended: host the model on the Hugging Face Hub and drop the Dropbox link. |
| 7 | Low | **Training script crashed without a GPU** (`torch.cuda.get_device_name(0)`) and imported Streamlit for no reason. | **Fixed.** |
| 8 | Low | **Personal name and email in every commit** (and on the Hugging Face remote). | **Fixed.** History rewritten to a single commit with a generic identity on both GitHub and the Space. |
| 9 | Info | A 236 MB model zip lives in Git LFS history. Harmless, but it makes the repository heavy to clone fully. | Open, optional cleanup with the history rewrite. |

## What was checked and found fine

- **Secrets:** the full git history was searched for tokens, keys and passwords. The only sensitive-looking string was the Dropbox link in #6.
- **Model file format:** weights are `safetensors`, which cannot execute code when loaded (unlike pickle-based `.bin` files).
- **Output handling:** the pasted email is only ever shown in Streamlit's own text widgets. The few pieces of custom HTML in the UI (the verdict card) contain only fixed text and numbers the app formats itself, never the email, so there is no script-injection path. Links found in an email are shown defanged (`hxxp://example[.]com`) so they cannot be clicked by accident.
- **Container:** the Docker image runs as an unprivileged user, not root, and ships only the app, not the data or the git history.
- **Codespaces setup:** the one-click config turns off Streamlit's CORS/XSRF checks because GitHub's port-forwarding proxy requires it; the forwarded port is private to the signed-in user by default.
- **Privacy:** pasted text is processed in memory on the machine running the app and is not written to disk or logged by this code. (If the app is hosted, for example as a public Hugging Face Space, the host sees the traffic: do not paste private mail into a public deployment.)

## Limits that no code change fixes

- The model reads text only. A phishing email that is well written, or that hides its payload in an image, attachment or look-alike link domain, can pass.
- It was trained on one English dataset. Attackers can paraphrase a message until it scores "safe" (an adversarial-evasion attack); the score is a hint, not proof.
- Confidence is often near 100% either way and should not be read as a calibrated probability.

## Reproducing this review

```bash
pip install pip-audit && pip-audit -r requirements.txt     # dependency check
python -m unittest discover -s tests -v                    # download-safety and cleaning tests
python -m phishing_detector.evaluate                       # accuracy table
```
