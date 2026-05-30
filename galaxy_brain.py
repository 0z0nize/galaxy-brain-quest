#!/usr/bin/env python3
"""
Galaxy Brain achievement automation.

Workflow per iteration:
    1. Helper account creates a Q&A discussion in the target repository.
    2. Main account posts an answer (via `gh api graphql`, using the local
       GitHub CLI session).
    3. Helper account marks that answer as the accepted answer.

GitHub credits the *main* account with one "accepted answer", which counts
toward the Galaxy Brain achievement tiers (2 / 8 / 16 / 32).

Requirements:
    - `gh` CLI authenticated as the MAIN account (the account that should
      earn the achievement).
    - A Personal Access Token for the HELPER account with the following
      scopes: `repo`, `write:discussion`, `read:discussion`.
    - The HELPER account must be a collaborator on the target repository
      (push permission is enough to create discussions and mark answers).
    - The target repository must be public and have Discussions enabled
      with a Q&A category.

Environment variables (all required):
    HELPER_TOKEN     Personal Access Token of the helper account
    REPO_OWNER       Owner login of the target repository (e.g. "0z0nize")
    REPO_NAME        Repository name (e.g. "galaxy-brain-quest")
    TARGET_COUNT     How many accepted answers to generate (default: 32)

Usage:
    export HELPER_TOKEN=ghp_xxx
    export REPO_OWNER=0z0nize
    export REPO_NAME=galaxy-brain-quest
    export TARGET_COUNT=32
    python3 galaxy_brain.py

Notes:
    - The script discovers the repository node ID and the Q&A category ID
      automatically via the GraphQL API.
    - A short delay between iterations reduces the chance of secondary
      rate-limit responses.
    - This script is intended for personal achievement automation in your
      own repository. Do not use it to spam other people's repositories.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request


GRAPHQL_URL = "https://api.github.com/graphql"


# A pool of ML/NLP themed questions. The script cycles through them and
# appends a unique counter so each discussion title is distinct.
TOPICS: list[tuple[str, str]] = [
    ("Best embedding model for Russian text",
     "Which model gives the best results for Russian-language semantic similarity?"),
    ("BERTopic vs LDA for short texts",
     "Which approach works better for clustering short user messages?"),
    ("HDBSCAN min_cluster_size tuning",
     "How do you pick the right min_cluster_size for dialogue intent clustering?"),
    ("UMAP n_neighbors selection",
     "What is a good rule of thumb for n_neighbors in UMAP?"),
    ("Fine-tuning ruBERT for classification",
     "Recommended learning rate and batch size for ruBERT fine-tuning?"),
    ("Whisper for Russian transcription",
     "How to improve Whisper accuracy on noisy Russian audio?"),
    ("Sentence-transformers vs LaBSE",
     "Which is better for multilingual semantic search?"),
    ("Handling class imbalance in NLP",
     "Best techniques for imbalanced intent classification?"),
    ("Evaluation metrics for clustering",
     "Beyond silhouette score, which metrics are useful?"),
    ("Hierarchical intent modeling",
     "How to structure a two-level intent taxonomy?"),
    ("Prompt engineering for classification",
     "Should I use few-shot or instruction-style prompts?"),
    ("Vector database choice",
     "FAISS vs Qdrant vs Pinecone for production?"),
    ("Chunking strategy for RAG",
     "Optimal chunk size for Russian docs in RAG pipelines?"),
    ("Active learning for annotation",
     "How to bootstrap annotation with active learning?"),
    ("Multi-label vs multi-class",
     "When to choose multi-label over multi-class for intents?"),
    ("Dealing with code-switching",
     "How to handle Russian-English code-switching in dialogues?"),
    ("Cross-validation for embeddings",
     "Best practice for CV with embedding-based pipelines?"),
    ("Topic coherence metrics",
     "C_v vs C_npmi - which to optimize?"),
    ("Tokenizer for Russian morphology",
     "BPE vs WordPiece vs SentencePiece for Russian?"),
    ("Distilling large LLMs",
     "How to distill a 70B model into a smaller student?"),
    ("Yandex Cloud GPU setup",
     "Best practices for ML workloads on Yandex Cloud?"),
    ("Git LFS for ML models",
     "When to use Git LFS vs DVC vs HuggingFace Hub?"),
    ("CI/CD for ML pipelines",
     "Recommended tools for ML CI/CD?"),
    ("Reproducibility seeds",
     "Which seeds need to be fixed for full reproducibility?"),
    ("MLflow vs W&B",
     "Which experiment tracker integrates better with Optuna?"),
    ("Dataset versioning",
     "DVC vs Quilt for dataset versioning?"),
    ("Batch inference optimization",
     "Tips for faster batch inference on GPU?"),
    ("ONNX export for transformers",
     "Common pitfalls when exporting BERT to ONNX?"),
    ("Quantization for deployment",
     "INT8 vs FP16 — tradeoffs in practice?"),
    ("Annotation tools comparison",
     "Label Studio vs Prodigy for NLP?"),
    ("Model drift detection",
     "How to detect drift in production NLP models?"),
    ("Synthetic data generation",
     "Can LLM-generated data replace human annotation?"),
]


ANSWER_TEMPLATE = (
    "For #{i}: Based on practical experience with Russian NLP, I recommend "
    "starting with established baselines (LaBSE for embeddings, ruBERT for "
    "classification) and using HDBSCAN with min_cluster_size between 15-30. "
    "UMAP defaults usually work; tune n_neighbors=15 first. For evaluation, "
    "combine c_v topic coherence with manual review of top terms. Always fix "
    "random seeds and use stratified CV for imbalanced data."
)


def require_env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if not value:
        sys.exit(f"Missing required environment variable: {name}")
    return value


def gql_helper(query: str, token: str) -> dict:
    """Run a GraphQL query authenticated as the helper account."""
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=json.dumps({"query": query}).encode(),
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "galaxy-brain-quest-script",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        sys.exit(f"Helper GraphQL HTTP error {exc.code}: {exc.read().decode()}")


def gql_main(query: str) -> dict:
    """Run a GraphQL query using the local `gh` CLI session (main account)."""
    result = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={query}"],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ},
    )
    if result.returncode != 0:
        sys.exit(f"gh api failed: {result.stderr.strip()}")
    return json.loads(result.stdout)


def fetch_repo_metadata(owner: str, name: str, token: str) -> tuple[str, str]:
    """Look up the repository node ID and the Q&A discussion category ID."""
    query = f"""
    query {{
      repository(owner: "{owner}", name: "{name}") {{
        id
        discussionCategories(first: 25) {{
          nodes {{ id name slug }}
        }}
      }}
    }}
    """
    data = gql_helper(query, token)
    repo = data.get("data", {}).get("repository")
    if not repo:
        sys.exit(f"Repository {owner}/{name} not found or not accessible.")
    repo_id = repo["id"]
    categories = repo["discussionCategories"]["nodes"]
    qa_category = next((c for c in categories if c["slug"] == "q-a"), None)
    if qa_category is None:
        sys.exit(
            "No 'Q&A' discussion category found. "
            "Enable Discussions and create a Q&A category in the target repo."
        )
    return repo_id, qa_category["id"]


def create_discussion(repo_id: str, category_id: str, title: str, body: str,
                       token: str) -> str | None:
    mutation = f"""
    mutation {{
      createDiscussion(input: {{
        repositoryId: "{repo_id}",
        categoryId: "{category_id}",
        title: {json.dumps(title)},
        body: {json.dumps(body)}
      }}) {{
        discussion {{ id number }}
      }}
    }}
    """
    response = gql_helper(mutation, token)
    if "errors" in response:
        print("createDiscussion errors:", response["errors"])
        return None
    return response["data"]["createDiscussion"]["discussion"]["id"]


def add_answer(discussion_id: str, body: str) -> str | None:
    mutation = f"""
    mutation {{
      addDiscussionComment(input: {{
        discussionId: "{discussion_id}",
        body: {json.dumps(body)}
      }}) {{
        comment {{ id }}
      }}
    }}
    """
    response = gql_main(mutation)
    if "errors" in response:
        print("addDiscussionComment errors:", response["errors"])
        return None
    return response["data"]["addDiscussionComment"]["comment"]["id"]


def mark_accepted(comment_id: str, token: str) -> bool:
    mutation = f"""
    mutation {{
      markDiscussionCommentAsAnswer(input: {{
        id: "{comment_id}"
      }}) {{
        discussion {{ isAnswered }}
      }}
    }}
    """
    response = gql_helper(mutation, token)
    if "errors" in response:
        print("markDiscussionCommentAsAnswer errors:", response["errors"])
        return False
    return response["data"]["markDiscussionCommentAsAnswer"]["discussion"]["isAnswered"]


def main() -> None:
    helper_token = require_env("HELPER_TOKEN")
    owner = require_env("REPO_OWNER")
    name = require_env("REPO_NAME")
    target = int(require_env("TARGET_COUNT", "32"))

    print(f"Target: {target} accepted answers in {owner}/{name}")
    repo_id, category_id = fetch_repo_metadata(owner, name, helper_token)
    print(f"Repository node ID: {repo_id}")
    print(f"Q&A category ID:    {category_id}")

    success = 0
    for i in range(1, target + 1):
        title_base, body_base = TOPICS[(i - 1) % len(TOPICS)]
        title = f"{title_base} #{i}"
        body = f"{body_base}\n\n(Question #{i})"

        discussion_id = create_discussion(repo_id, category_id, title, body,
                                          helper_token)
        if discussion_id is None:
            continue

        comment_id = add_answer(discussion_id, ANSWER_TEMPLATE.format(i=i))
        if comment_id is None:
            continue

        if mark_accepted(comment_id, helper_token):
            success += 1
            print(f"#{i:>2}  accepted   ({success}/{target})")

        time.sleep(0.3)

    print(f"\nDone: {success}/{target} accepted answers.")


if __name__ == "__main__":
    main()
