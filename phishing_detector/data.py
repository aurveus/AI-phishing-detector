"""Load the dataset and split it the same way everywhere."""
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from . import config
from .preprocess import clean_text

LABEL_IDS = {"Safe Email": 0, "Phishing Email": 1}


def load_dataset(csv_path: Path = config.DATA_CSV) -> pd.DataFrame:
    """Columns: raw (original text), text (cleaned), label (0 safe, 1 phishing). Missing text rows are dropped."""
    df = pd.read_csv(csv_path).dropna(subset=["Email Text"])
    out = pd.DataFrame({"raw": df["Email Text"].astype(str).values})
    out["text"] = out["raw"].map(clean_text)
    out["label"] = df["Email Type"].map(LABEL_IDS).values
    return out


def original_split(df: pd.DataFrame):
    """The 80/20 split the published model was trained with (indices only). Same call, same seed as the old script."""
    return train_test_split(range(len(df)), test_size=0.2, random_state=config.SEED)


def leak_free_test_indices(df: pd.DataFrame, train_idx, test_idx) -> list:
    """Test rows whose cleaned text does not also appear in the training rows."""
    seen = set(df["text"].iloc[list(train_idx)])
    return [i for i in test_idx if df["text"].iloc[i] not in seen]
