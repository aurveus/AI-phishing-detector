"""Fine-tune DistilBERT on the phishing email dataset.

  python -m phishing_detector.train                       # full run (GPU recommended)
  python -m phishing_detector.train --max-samples 400 --epochs 1 --out /tmp/smoke   # quick check that it works

Compared with the first version of this script (kept in git history):
  * identical emails are removed before splitting, so no test email also appears in training,
  * a separate validation set picks the best epoch; the test set is only used once, at the end,
  * it runs on CPU too, and the result is reproducible (seeded).
The published model was trained with the first version (80/20 split, test set used for model selection). See
docs/SECURITY_AND_REVIEW.md for what that means for the reported numbers.
"""
import argparse
import os

import numpy as np
import torch
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from transformers import DistilBertForSequenceClassification, DistilBertTokenizerFast, Trainer, TrainingArguments, set_seed

from . import config
from .data import load_dataset

BASE_MODEL = "distilbert-base-uncased"


class EmailDataset(torch.utils.data.Dataset):
    """Wraps tokenizer output and labels so the Trainer can index them."""

    def __init__(self, encodings, labels):
        self.encodings, self.labels = encodings, list(labels)

    def __getitem__(self, i):
        item = {k: torch.tensor(v[i]) for k, v in self.encodings.items()}
        item["labels"] = torch.tensor(self.labels[i])
        return item

    def __len__(self):
        return len(self.labels)


def metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    p, r, f1, _ = precision_recall_fscore_support(labels, preds, average="binary", zero_division=0)
    return {"accuracy": accuracy_score(labels, preds), "precision": p, "recall": r, "f1": f1}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", default=str(config.DATA_CSV))
    ap.add_argument("--out", default=str(config.MODEL_DIR), help="where the final model is saved")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--lr", type=float, default=5e-5)
    ap.add_argument("--max-samples", type=int, default=0, help="use only this many emails (smoke test)")
    args = ap.parse_args()

    set_seed(config.SEED)
    print("GPU available:", torch.cuda.is_available())

    if not os.path.exists(args.csv):
        raise SystemExit(f"Dataset not found: {args.csv}
Download Phishing_Email.csv (see the README) and put it there, or pass --csv.")
    df = load_dataset(args.csv)
    before = len(df)
    df = df.drop_duplicates(subset="text").reset_index(drop=True)
    print(f"{before} emails, {before - len(df)} duplicates removed, {len(df)} left")
    if args.max_samples:
        df = df.sample(n=min(args.max_samples, len(df)), random_state=config.SEED).reset_index(drop=True)

    # 80% train, 10% validation (choose the epoch), 10% test (reported once)
    train_df, rest = train_test_split(df, test_size=0.2, random_state=config.SEED, stratify=df["label"])
    val_df, test_df = train_test_split(rest, test_size=0.5, random_state=config.SEED, stratify=rest["label"])
    print("train / validation / test:", len(train_df), len(val_df), len(test_df))

    tok = DistilBertTokenizerFast.from_pretrained(BASE_MODEL)

    def encode(frame):
        enc = tok(list(frame["text"]), truncation=True, padding=True, max_length=config.MAX_TOKENS)
        return EmailDataset(enc, frame["label"])

    model = DistilBertForSequenceClassification.from_pretrained(BASE_MODEL, num_labels=2)
    trainer = Trainer(
        model=model,
        args=TrainingArguments(
            output_dir="./results", eval_strategy="epoch", save_strategy="epoch", learning_rate=args.lr,
            per_device_train_batch_size=args.batch_size, per_device_eval_batch_size=args.batch_size,
            num_train_epochs=args.epochs, weight_decay=0.01, logging_steps=50, load_best_model_at_end=True,
            metric_for_best_model="loss", seed=config.SEED, report_to="none",
        ),
        train_dataset=encode(train_df), eval_dataset=encode(val_df), compute_metrics=metrics,
    )
    trainer.train()
    print("Test results:", trainer.evaluate(encode(test_df), metric_key_prefix="test"))

    model.save_pretrained(args.out)
    tok.save_pretrained(args.out)
    print("Model and tokenizer saved to", args.out)


if __name__ == "__main__":
    main()
