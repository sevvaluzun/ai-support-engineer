
import json
import re
from pathlib import Path

KNOWLEDGE_BASE = Path(__file__).with_name("knowledge_base.json")

STOP_WORDS = {
    "a", "an", "the", "and", "or", "to", "for",
    "in", "on", "at", "of", "is", "are", "be",
    "with", "when", "that", "this", "from",
    "users", "user", "customer", "customers",
    "check", "error", "errors", "issue", "issues",
    "application", "service"
}


def tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {
        word for word in words
        if word not in STOP_WORDS and len(word) > 1
    }


def retrieve_documents(query: str, top_k: int = 2):
    with KNOWLEDGE_BASE.open("r", encoding="utf-8") as file:
        documents = json.load(file)

    query_words = tokenize(query)
    results = []

    for document in documents:
        title_words = tokenize(document["title"])
        content_words = tokenize(document["content"])

        title_matches = len(query_words & title_words)
        content_matches = len(query_words & content_words)

        score = title_matches * 3 + content_matches

        if score >= 2:
            results.append((score, document))

    results.sort(key=lambda item: item[0], reverse=True)

    if not results:
        return []

    best_score = results[0][0]
    minimum_score = max(2, best_score * 0.5)

    return [
        document
        for score, document in results
        if score >= minimum_score
    ][:top_k]


if __name__ == "__main__":
    for query in [
        "API Error 429 users receive HTTP 429",
        "Login Error users cannot log in",
        "Database connection timeout"
    ]:
        print(f"\nQUERY: {query}")
        results = retrieve_documents(query)
        print([doc["title"] for doc in results])
