# # scripts/build_embeddings.py

# import os
# import numpy as np
# from datasets import load_dataset
# from sentence_transformers import SentenceTransformer

# EMBEDDINGS_PATH = "./data/embeddings.npy"


# def build_embeddings():
#     print("Loading dataset...")

#     ds = load_dataset("Amod/mental_health_counseling_conversations")
#     df = ds["train"].to_pandas()

#     df = (
#         df.drop_duplicates(subset=["Context", "Response"])
#         .dropna()
#         .reset_index(drop=True)
#     )

#     print(f"Loaded {len(df)} records")

#     print("Loading model...")
#     model = SentenceTransformer("BAAI/bge-small-en-v1.5")

#     print("Generating embeddings...")
#     embeddings = model.encode(
#         df["Context"].tolist(),
#         batch_size=64,
#         show_progress_bar=True,
#         normalize_embeddings=True,
#     )

#     os.makedirs("./data", exist_ok=True)
#     np.save(EMBEDDINGS_PATH, embeddings)

#     print(f"Saved embeddings to {EMBEDDINGS_PATH}")


# if __name__ == "__main__":
#     build_embeddings()

# scripts/build_embeddings.py

import os
import numpy as np
from datasets import load_dataset
from sentence_transformers import SentenceTransformer

EMBEDDINGS_PATH = "./data/embeddings.npy"
DF_CACHE_PATH = "./data/qa_pairs.parquet"


def build_embeddings():
    print("Loading dataset...")

    ds = load_dataset("Amod/mental_health_counseling_conversations")
    df = ds["train"].to_pandas()

    df = (
        df[["Context", "Response"]]
        .drop_duplicates(subset=["Context", "Response"])
        .dropna()
        .reset_index(drop=True)
    )

    print(f"Loaded {len(df)} records")

    os.makedirs("./data", exist_ok=True)

    # Cache the cleaned corpus so the runtime container never needs to call
    # load_dataset() / pull from the HF Hub again on every boot.
    df.to_parquet(DF_CACHE_PATH, index=False)
    print(f"Cached corpus to {DF_CACHE_PATH}")

    print("Loading model...")
    model = SentenceTransformer("BAAI/bge-small-en-v1.5", device="cpu")

    print("Generating embeddings...")
    embeddings = model.encode(
        df["Context"].tolist(),
        batch_size=64,
        show_progress_bar=True,
        normalize_embeddings=True,
    )

    np.save(EMBEDDINGS_PATH, embeddings)
    print(f"Saved embeddings to {EMBEDDINGS_PATH}")


if __name__ == "__main__":
    build_embeddings()
