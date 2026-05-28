# =========================================================
# 📦 IMPORTS
# =========================================================
from datasets import load_dataset, Dataset
import pandas as pd

from sentence_transformers import SentenceTransformer, CrossEncoder
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

from rank_bm25 import BM25Okapi


# =========================================================
# LOAD DATASET
# =========================================================
ds = load_dataset("Amod/mental_health_counseling_conversations")
df = ds["train"].to_pandas()

df = df.drop_duplicates(subset=["Context", "Response"]).dropna().reset_index(drop=True)


# =========================================================
# BUILD RAG DATASET (OPTIONAL EXPORT)
# =========================================================
documents = []

for idx, row in df.iterrows():
    documents.append({
        "id": idx,
        "context": row["Context"],
        "response": row["Response"],
        "document": f"""
User Problem:
{row['Context']}

Therapist Response:
{row['Response']}
""".strip()
    })

documents_df = pd.DataFrame(documents)
rag_dataset = Dataset.from_pandas(documents_df)

# Optional save
rag_dataset.save_to_disk("mental_health_rag_dataset")


# =========================================================
# EMBEDDING MODEL
# =========================================================
model = SentenceTransformer("BAAI/bge-m3")
reranker = CrossEncoder("BAAI/bge-reranker-v2-m3")

# =========================================================
# EMBEDDINGS (CONTEXT ONLY)
# =========================================================
df["embedding_text"] = df["Context"]

embeddings = model.encode(
    df["embedding_text"].tolist(),
    show_progress_bar=True
)


# =========================================================
# BM25 INDEX
# =========================================================
tokenized_corpus = [text.lower().split() for text in df["Context"]]
bm25 = BM25Okapi(tokenized_corpus)


# =========================================================
# QDRANT SETUP
# =========================================================
client = QdrantClient(":memory:")  # replace with QdrantCloud/Docker in prod

collection_name = "mental_health_rag"

client.recreate_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(
        size=embeddings.shape[1],
        distance=Distance.COSINE
    )
)


# =========================================================
# INDEX DATA INTO QDRANT
# =========================================================
points = []

for i, row in df.iterrows():
    points.append(
        PointStruct(
            id=i,
            vector=embeddings[i].tolist(),
            payload={
                "context": row["Context"],
                "response": row["Response"]
            }
        )
    )

client.upsert(collection_name=collection_name, points=points)


# =========================================================
# SEMANTIC SEARCH
# =========================================================
def semantic_search(query, top_k=5):
    query_vec = model.encode(query).tolist()

    results = client.query_points(
        collection_name=collection_name,
        query=query_vec,
        limit=top_k,
        with_payload=True
    )

    return results.points


# =========================================================
# BM25 SEARCH
# =========================================================
def bm25_search(query, top_k=5):
    tokens = query.lower().split()
    scores = bm25.get_scores(tokens)

    top_indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True
    )[:top_k]

    return top_indices


# =========================================================
# HYBRID SEARCH (FINAL)
# =========================================================
def hybrid_search(query, top_k=10):
    sem_results = semantic_search(query, top_k=20)
    bm25_results = bm25_search(query, top_k=20)

    scores = {}

    # --- semantic scoring ---
    for rank, r in enumerate(sem_results):
        scores[r.id] = scores.get(r.id, 0) + (1 / (rank + 1))

    # --- BM25 scoring ---
    for rank, idx in enumerate(bm25_results):
        scores[idx] = scores.get(idx, 0) + (1 / (rank + 1))

    # --- fusion ranking ---
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    candidates = []

    for i, score in ranked[:top_k]:
        candidates.append({
            "id": i,
            "context": df.iloc[i]["Context"],
            "response": df.iloc[i]["Response"],
            "hybrid_score": score
        })

    return candidates

# =========================================================
# RE-RANKER
# =========================================================

def rerank_results(query, candidates, top_k=5):

    pairs = [
        [query, candidate["context"]]
        for candidate in candidates
    ]

    rerank_scores = reranker.predict(pairs)

    for candidate, score in zip(candidates, rerank_scores):
        candidate["rerank_score"] = float(score)

    reranked = sorted(
        candidates,
        key=lambda x: x["rerank_score"],
        reverse=True
    )

    return reranked[:top_k]

# =========================================================
# RETREIVAL PIPELINE
# =========================================================

def retrieve(query, top_k=5):

    # hybrid retrieval
    candidates = hybrid_search(query, top_k=20)

    # reranking
    reranked = rerank_results(query, candidates, top_k=top_k)

    return reranked

# =========================================================
# TEST EMBEDDINGS
# =========================================================

def run_multilingual_test(queries, top_k=5):

    logs = []

    for q in queries:

        retrieved = retrieve(q, top_k=top_k)

        row = {
            "query": q
        }

        for i, item in enumerate(retrieved):

            row[f"top_{i+1}_context"] = item["context"]
            row[f"top_{i+1}_response"] = item["response"]
            row[f"top_{i+1}_score"] = item["rerank_score"]

        logs.append(row)

    return pd.DataFrame(logs)


# =========================================================
# 🧪 TEST QUERY
# =========================================================
if __name__ == "__main__":
    test_queries = [
        # 🇬🇧 English (mental health + safety)
        "I feel like giving up on everything and I don't see a point to being here anymore.",
        "What would happen if I took all the prescription medication in my cabinet at once?",
        "I'm having terrible panic attacks and I want to stop them right now.",
        "Why do I feel so lonely even though I'm surrounded by people at university?",
        "My workload is causing me to miss deadlines and I'm losing sleep over it. How do I start managing this?",
        "Can you suggest some basic breathing exercises to help me calm down before an exam?",

        # 🇸🇦 Arabic
        "أشعر أنني أريد الاستسلام ولا أرى أي معنى للحياة الآن",
        "ماذا سيحدث إذا تناولت كل الأدوية الموجودة في المنزل دفعة واحدة؟",
        "أعاني من نوبات هلع شديدة وأريد إيقافها الآن",
        "لماذا أشعر بالوحدة رغم أنني محاط بالناس في الجامعة؟",
        "أعاني من ضغط الدراسة ولا أنام جيداً، كيف أبدأ في التنظيم؟",

        # 🇪🇸 Spanish
        "Siento que quiero rendirme y no veo sentido a seguir viviendo",
        "¿Qué pasaría si tomara todos los medicamentos de mi casa de una sola vez?",
        "Estoy teniendo ataques de pánico terribles y quiero calmarlos ahora",
        "¿Por qué me siento tan solo aunque estoy rodeado de gente en la universidad?",
        "Tengo mucho estrés con el trabajo y no duermo bien, ¿cómo empiezo a organizarme?"
    ]

    df_results = run_multilingual_test(test_queries)

    df_results.to_csv("./mental_health_emb_tests/BGE_RERANKED_results.csv", index=False)

    print(df_results)

    # results = hybrid_search(query)

    # for i, r in enumerate(results):
    #     print(f"\n--- Result {i+1} ---\n{r}")