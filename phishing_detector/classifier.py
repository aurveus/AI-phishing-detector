"""Load the model once and classify email text."""
from pathlib import Path

import torch
from transformers import DistilBertForSequenceClassification, DistilBertTokenizerFast

from . import config
from .preprocess import clean_text


class PhishingClassifier:
    def __init__(self, model_dir: Path = config.MODEL_DIR):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = DistilBertTokenizerFast.from_pretrained(model_dir)
        self.model = DistilBertForSequenceClassification.from_pretrained(model_dir).to(self.device).eval()

    @torch.no_grad()
    def predict_batch(self, texts, clean: bool = True, max_tokens: int = config.MAX_TOKENS):
        """Return a list of (label_id, phishing_probability). `clean=False` only exists to reproduce old behaviour."""
        texts = [clean_text(t) if clean else t for t in texts]
        enc = self.tokenizer(texts, return_tensors="pt", truncation=True, padding=True, max_length=max_tokens)
        logits = self.model(**{k: v.to(self.device) for k, v in enc.items()}).logits
        probs = torch.softmax(logits, dim=1)[:, 1].cpu().tolist()
        return [(int(p >= 0.5), p) for p in probs]

    def predict(self, text: str) -> dict:
        if not text or not text.strip():
            raise ValueError("empty text")
        if len(text) > config.MAX_INPUT_CHARS:
            raise ValueError(f"text is longer than {config.MAX_INPUT_CHARS} characters")
        label_id, p = self.predict_batch([text])[0]
        return {"label": config.LABELS[label_id], "phishing_probability": p}
