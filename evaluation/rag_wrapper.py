import sys
import os

# allow import from project root
sys.path.append(os.path.abspath(".."))

from rag_pipeline import rag_pipeline


def run_rag(query: str):
    result = rag_pipeline(
        query=query,
        chat_history="",
        language="en",
        emotion="neutral",
        return_metadata=True
    )

    return {
        "answer": result["response"],
        "contexts": [
            c["context"] for c in result["retrieved_contexts"]
        ]
    }