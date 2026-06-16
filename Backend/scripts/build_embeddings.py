# scripts/build_embeddings.py

import os
import numpy as np
from datasets import load_dataset
from sentence_transformers import SentenceTransformer

EMBEDDINGS_PATH = "./data/embeddings.npy"


def build_embeddings():
    print("Loading dataset...")

    ds = load_dataset("Amod/mental_health_counseling_conversations")
    df = ds["train"].to_pandas()

    df = (
        df.drop_duplicates(subset=["Context", "Response"])
        .dropna()
        .reset_index(drop=True)
    )

    print(f"Loaded {len(df)} records")

    print("Loading model...")
    model = SentenceTransformer("BAAI/bge-m3")

    print("Generating embeddings...")
    embeddings = model.encode(
        df["Context"].tolist(),
        batch_size=64,
        show_progress_bar=True,
        normalize_embeddings=True,
    )

    os.makedirs("./data", exist_ok=True)
    np.save(EMBEDDINGS_PATH, embeddings)

    print(f"Saved embeddings to {EMBEDDINGS_PATH}")


if __name__ == "__main__":
    build_embeddings()
