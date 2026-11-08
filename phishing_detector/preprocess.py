"""Text cleaning shared by training, evaluation and the app.

The model was trained on text cleaned this way, so the app must clean input the same way. (The original app
skipped this step and measurably missed more phishing emails; see docs/SECURITY_AND_REVIEW.md.)
"""
import re

_URL = re.compile(r"http\S+")
_EMAIL = re.compile(r"\S+@\S+")
_NON_LETTERS = re.compile(r"[^a-zA-Z\s]")


def clean_text(text: str) -> str:
    """Lower-case, replace links and addresses with the words "url" / "email", drop everything but letters."""
    text = text.lower()
    text = _URL.sub("url", text)
    text = _EMAIL.sub("email", text)
    return _NON_LETTERS.sub("", text)
