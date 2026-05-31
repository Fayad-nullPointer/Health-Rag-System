import pandas as pd
import time

from deepeval.test_case import LLMTestCase
from deepeval.metrics import (
    FaithfulnessMetric,
    AnswerRelevancyMetric,
)

from rag_wrapper import run_rag
from groq_llm import GroqLLM
from gemini_llm import GeminiLLM
from dataset_builder import eval_queries


def run_evaluation():

    llm = GroqLLM()

    metrics = [
        FaithfulnessMetric(model=llm),
        AnswerRelevancyMetric(model=llm),
    ]

    results = []

    for item in eval_queries:

        query = item["query"]

        try:
            result = run_rag(query)

            test_case = LLMTestCase(
                input=query,
                actual_output=result["answer"],
                retrieval_context=result["contexts"]
            )

            row = {
                "query": query,
                "answer": result["answer"]
            }

            print("\n========================")
            print("QUERY:", query)

            for metric in metrics:

                try:
                    metric.measure(test_case)

                    row[metric.__class__.__name__] = metric.score

                    print(
                        f"{metric.__class__.__name__}: "
                        f"{metric.score:.4f}"
                    )

                except Exception as e:

                    row[metric.__class__.__name__] = None

                    print(
                        f"{metric.__class__.__name__}: FAILED"
                    )
                    print(f"Reason: {e}")

            results.append(row)

            # Save progress after every query
            pd.DataFrame(results).to_csv(
                "evaluation_results.csv",
                index=False
            )

            time.sleep(120)

        except Exception as e:

            print(f"\n❌ Failed query: {query}")
            print(f"Reason: {e}")

            results.append({
                "query": query,
                "answer": None,
                "FaithfulnessMetric": None,
                "AnswerRelevancyMetric": None,
                "error": str(e)
            })

            pd.DataFrame(results).to_csv(
                "evaluation_results.csv",
                index=False
            )

            continue


if __name__ == "__main__":
    run_evaluation()