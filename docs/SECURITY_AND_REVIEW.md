# Security and code review

I went through the whole repository: the code, the dependencies, the git history, and how the app handles what people paste into it. I read the code, ran `pip-audit` on the dependency versions, searched the full history for secrets, and ran the app, the tests and the evaluation.

## What I found

**1. Old dependencies with known vulnerabilities (high, fixed).**
The pinned versions of `torch` (2.5.1), `transformers` (4.33.2) and `streamlit` (1.24.1) had 81 known vulnerabilities between them according to `pip-audit`. The pins also didn't match what was actually installed and working, and the training script used a setting (`eval_strategy`) that doesn't exist in that old `transformers`, so the pinned file couldn't even run the training code. `requirements.txt` now sets minimum versions that include the fixes. A clean install pulled in the current releases, the app and tests pass on them, and `pip-audit` reports nothing for the project's own packages.

**2. The model download wasn't checked (medium, fixed).**
The app downloaded a zip from a hardcoded Dropbox link with no timeout, no check that the request succeeded, no size limit and no integrity check, then unzipped it with `extractall`. A swapped or corrupted file would have been loaded without anyone noticing. Now the download is https-only with a timeout and a size cap, it's unzipped into a temp folder with a check that nothing escapes that folder, and every file is compared with a SHA-256 checksum before it's used. There are tests for a tampered file and a malicious archive. I also ran the real download once to make sure the checksums match the actual file on Dropbox.

**3. No limit on input size (medium, fixed).**
The text box took any amount of text. The dataset itself contains a 15-million-character "email", so huge inputs do happen, and on a public deployment they're a cheap way to eat memory. There's now a 20,000-character cap, the model only looks at the first 128 tokens, inference runs without gradients, and the model is loaded once instead of on every click.

**4. Training and the app cleaned text differently (medium, fixed).**
Training lowercased the text, swapped links and addresses for placeholder words and stripped everything but letters. The app fed the model the raw text. Both now use one shared cleaning function. Measured on the test split, the raw version missed 45 phishing emails instead of 29.

**5. How the original model was evaluated (medium, measured, not retrained).**
The original run used the test set to pick the best epoch, and 384 of the 3,727 test emails (about 10%) also appear in the training data, so the reported accuracy could be too optimistic. I checked: on the 3,343 test emails the model never saw, accuracy is 98.3%, slightly higher, so the headline number holds. `train.py` now removes duplicates and keeps separate validation and test sets for future runs, but I didn't retrain the published model.

**6. The Dropbox link is in the code and history (low, mitigated).**
The share link, including its `rlkey` access key, is in the source. It points at a public model, so it isn't a leaked password, but that key can't be scrubbed from anything that already copied it. It now lives in `config.py` and can be overridden with `MODEL_URL`, and the checksums protect the file's integrity. The cleaner long-term fix is to host the model on the Hugging Face Hub and drop the Dropbox link.

**7. The training script crashed on machines without a GPU (low, fixed).**
It called `torch.cuda.get_device_name(0)` unconditionally, and it imported Streamlit for no reason.

**8. Personal name and email in the commit history (low, fixed).**
Every old commit carried them, on GitHub and on the Hugging Face Space. The history is now a single commit under a generic identity on both. (Git LFS had also been tracking a 236 MB model zip in the old history, which is gone with it.)

## Things I checked that were fine

- **Secrets.** I searched the entire git history for tokens, keys and passwords. The only sensitive-looking string was the Dropbox link from point 6.
- **The model file format.** The weights are `safetensors`, which can't run code when loaded, unlike pickle-based `.bin` files.
- **Output handling.** The pasted email is only ever shown inside Streamlit's own text widgets. The one bit of custom HTML (the verdict card) contains only fixed text and numbers the app formats itself, never the email, so there's no way to inject a script through it. Links found in an email are shown defanged (`hxxp://example[.]com`) so nobody clicks one by accident.
- **Privacy.** Pasted text is handled in memory and isn't written to disk or logged by this code. If you host the app somewhere public, the host can still see the traffic, so don't paste private mail into a public deployment.
- **The container.** The Docker image runs as a normal user, not root, and contains only the app, not the data or the git history.
- **The Codespaces setup.** It turns off Streamlit's CORS and XSRF checks because GitHub's port-forwarding proxy needs that. The forwarded port is private to the signed-in user by default.

## What code can't fix

- The model only reads text. A well-written phishing email, or one that hides its payload in an image, an attachment or a look-alike domain, can get through.
- It was trained on a single English dataset. Someone who knows how it works can reword a message until it scores as safe.
- The confidence number is often close to 100% either way. Don't read it as a true probability.

## Checking this yourself

```bash
pip install pip-audit && pip-audit -r requirements.txt   # dependency check
python -m unittest discover -s tests -v                  # download-safety, cleaning and UI tests
python -m phishing_detector.evaluate                     # the accuracy table
```
