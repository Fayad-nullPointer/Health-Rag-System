#!/usr/bin/env python3
"""
build_embeddings.py - Generate embeddings for RAG pipeline

This script is designed to run:
1. Locally for development
2. In GitHub Actions CI/CD pipeline
3. Independent of Docker

Output: data/embeddings.npy (~10-50 MB depending on model)

Usage:
    python build_embeddings.py --model BAAI/bge-m3 --output data/embeddings.npy
    python build_embeddings.py --model sentence-transformers/all-MiniLM-L6-v2 --output data/embeddings.npy
"""

import os
import sys
import argparse
import logging
import numpy as np
from pathlib import Path
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def build_embeddings(
    model_name: str = "BAAI/bge-m3",
    output_path: str = "data/embeddings.npy",
    dataset_name: str = "Amod/mental_health_counseling_conversations",
    use_cache: bool = True,
    batch_size: int = 32,
    device: str = "cpu",
) -> np.ndarray:
    """
    Generate embeddings for the mental health dataset.

    Args:
        model_name: HuggingFace model identifier
        output_path: Path to save embeddings.npy
        dataset_name: HuggingFace dataset identifier
        use_cache: Use local cache for model and dataset
        batch_size: Batch size for embedding generation
        device: Device to use ('cpu' or 'cuda')

    Returns:
        np.ndarray: Generated embeddings array
    """

    try:
        from datasets import load_dataset
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        logger.error(f"Missing required package: {e}")
        logger.info("Install with: pip install datasets sentence-transformers pandas")
        sys.exit(1)

    logger.info(f"Loading dataset: {dataset_name}")
    try:
        # Load dataset with caching
        dataset = load_dataset(
            dataset_name,
            cache_dir=".cache" if use_cache else None,
            trust_remote_code=True,
        )
        df = dataset["train"].to_pandas()
    except Exception as e:
        logger.error(f"Failed to load dataset: {e}")
        raise

    logger.info(f"Dataset loaded: {len(df)} records")

    # Clean data
    df = (
        df.drop_duplicates(subset=["Context", "Response"])
        .dropna()
        .reset_index(drop=True)
    )
    logger.info(f"After cleaning: {len(df)} records")

    logger.info(f"Loading model: {model_name}")
    try:
        model = SentenceTransformer(
            model_name,
            cache_folder=".cache" if use_cache else None,
            device=device,
            trust_remote_code=True,
        )
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise

    logger.info("Model loaded. Generating embeddings...")

    # Generate embeddings in batches
    contexts = df["Context"].tolist()
    embeddings_list = []

    total_batches = (len(contexts) + batch_size - 1) // batch_size
    for i in range(0, len(contexts), batch_size):
        batch = contexts[i : i + batch_size]
        batch_embeddings = model.encode(
            batch,
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        embeddings_list.append(batch_embeddings)

        current_batch = (i // batch_size) + 1
        logger.info(
            f"Processed batch {current_batch}/{total_batches} "
            f"({len(embeddings_list) * batch_size}/{len(contexts)} records)"
        )

    # Concatenate all embeddings
    embeddings = np.vstack(embeddings_list)
    logger.info(f"Embeddings shape: {embeddings.shape}")

    # Save embeddings
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    np.save(output_path, embeddings)
    file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
    logger.info(f"Embeddings saved to: {output_path} ({file_size:.2f} MB)")

    return embeddings


def fastembed_alternative(
    output_path: str = "data/embeddings_fastembed.npy",
    dataset_name: str = "Amod/mental_health_counseling_conversations",
    model_name: str = "BAAI/bge-small-en-v1.5",  # Smaller FastEmbed-compatible model
) -> Optional[np.ndarray]:
    """
    Alternative: Generate embeddings using FastEmbed (smaller, faster).

    FastEmbed advantages:
    - Much smaller model files (~50-100 MB vs 500 MB)
    - Faster inference (~10x on CPU)
    - Minimal dependencies

    Args:
        output_path: Path to save embeddings
        dataset_name: HuggingFace dataset
        model_name: FastEmbed model name

    Returns:
        np.ndarray: Generated embeddings or None if FastEmbed unavailable
    """

    try:
        from fastembed import TextEmbedding
        from datasets import load_dataset
    except ImportError:
        logger.warning("FastEmbed not available. Install with: pip install fastembed")
        return None

    logger.info(f"Using FastEmbed model: {model_name}")

    try:
        dataset = load_dataset(dataset_name, cache_dir=".cache", trust_remote_code=True)
        df = dataset["train"].to_pandas()
        df = (
            df.drop_duplicates(subset=["Context", "Response"])
            .dropna()
            .reset_index(drop=True)
        )

        model = TextEmbedding(model_name=model_name, max_length=512)
        contexts = df["Context"].tolist()

        logger.info("Generating embeddings with FastEmbed...")
        embeddings_list = []
        for i, doc in enumerate(contexts):
            if (i + 1) % 100 == 0:
                logger.info(f"Processed {i + 1}/{len(contexts)} records")
            embedding = model.embed(doc)
            embeddings_list.append(embedding)

        embeddings = np.array(embeddings_list)
        logger.info(f"Embeddings shape: {embeddings.shape}")

        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        np.save(output_path, embeddings)
        file_size = os.path.getsize(output_path) / (1024 * 1024)
        logger.info(
            f"FastEmbed embeddings saved to: {output_path} ({file_size:.2f} MB)"
        )

        return embeddings

    except Exception as e:
        logger.error(f"FastEmbed generation failed: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Generate embeddings for RAG pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate embeddings with default model
  python build_embeddings.py
  
  # Use a lightweight model
  python build_embeddings.py --model sentence-transformers/all-MiniLM-L6-v2
  
  # Use FastEmbed (faster, smaller)
  python build_embeddings.py --fastembed
  
  # Custom output path
  python build_embeddings.py --output embeddings/mental_health.npy
  
  # Use CUDA GPU
  python build_embeddings.py --device cuda
        """,
    )

    parser.add_argument(
        "--model",
        default="BAAI/bge-m3",
        help="HuggingFace model name (default: BAAI/bge-m3)",
    )
    parser.add_argument(
        "--output",
        default="data/embeddings.npy",
        help="Output path for embeddings (default: data/embeddings.npy)",
    )
    parser.add_argument(
        "--dataset",
        default="Amod/mental_health_counseling_conversations",
        help="HuggingFace dataset name",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Batch size for embedding generation (default: 32)",
    )
    parser.add_argument(
        "--device",
        choices=["cpu", "cuda"],
        default="cpu",
        help="Device to use for inference (default: cpu)",
    )
    parser.add_argument(
        "--fastembed",
        action="store_true",
        help="Use FastEmbed for smaller, faster embeddings",
    )
    parser.add_argument(
        "--no-cache", action="store_true", help="Don't cache models and datasets"
    )

    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("Embedding Generation Pipeline")
    logger.info("=" * 70)

    try:
        if args.fastembed:
            logger.info("FastEmbed mode selected")
            result = fastembed_alternative(
                output_path=args.output,
                dataset_name=args.dataset,
            )
            if result is None:
                logger.warning(
                    "FastEmbed unavailable, falling back to SentenceTransformer"
                )
                build_embeddings(
                    model_name=args.model,
                    output_path=args.output,
                    dataset_name=args.dataset,
                    use_cache=not args.no_cache,
                    batch_size=args.batch_size,
                    device=args.device,
                )
        else:
            build_embeddings(
                model_name=args.model,
                output_path=args.output,
                dataset_name=args.dataset,
                use_cache=not args.no_cache,
                batch_size=args.batch_size,
                device=args.device,
            )

        logger.info("=" * 70)
        logger.info("Embedding generation completed successfully!")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"Embedding generation failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
