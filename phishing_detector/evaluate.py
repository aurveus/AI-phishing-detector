"""Score the saved model on the test split it was originally held out with.

  python -m phishing_detector.evaluate

Prints three rows: the app's current behaviour on the original test split, the same without the leak (test emails that
also appear in the training set removed), and the old app behaviour (raw text, 512 tokens) for comparison.
"""
import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support

from . import config
from .classifier import PhishingClassifier
from .data import leak_free_test_indices, load_dataset, original_split


def score(name, y_true, y_pred):
    p, r, f1, _ = precision_recall_fscore_support(y_true, y_pred, average="binary", zero_division=0)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    print(f"{name:<46} n={len(y_true):>5}  acc={accuracy_score(y_true, y_pred):.4f}  precision={p:.4f}  "
          f"recall={r:.4f}  f1={f1:.4f}  (missed phishing {fn}, false alarms {fp})")


def predict(clf, texts, clean, max_tokens):
    out = []
    for i in range(0, len(texts), 64):
        out += [label for label, _ in clf.predict_batch(texts[i:i + 64], clean=clean, max_tokens=max_tokens)]
    return np.array(out)


def main():
    df = load_dataset()
    train_idx, test_idx = original_split(df)
    clean_idx = leak_free_test_indices(df, train_idx, test_idx)
    clf = PhishingClassifier()
    y = df["label"].values

    cleaned = lambda idx: list(df["text"].iloc[idx])  # noqa: E731
    raw = lambda idx: list(df["raw"].iloc[idx])       # noqa: E731
    score("original test split, as the app runs now", y[test_idx], predict(clf, cleaned(test_idx), False, config.MAX_TOKENS))
    score("test split without train duplicates", y[clean_idx], predict(clf, cleaned(clean_idx), False, config.MAX_TOKENS))
    score("old app behaviour (raw text, 512 tokens)", y[test_idx], predict(clf, raw(test_idx), False, 512))


if __name__ == "__main__":
    main()
