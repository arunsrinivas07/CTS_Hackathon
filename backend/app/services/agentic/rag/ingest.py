"""
ingest.py
=========

CMS Knowledge Base Ingestion Script.
Loads authoritative CMS JSON policies, parses metadata and sections,
generates embeddings, and indexes them into the isolated Vector Store.

Run directly via:
    python -m tools.rag.ingest
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.llm.config import settings
from app.services.agentic.rag.embeddings import get_embedding_function
from app.services.agentic.rag.vector_store import get_vector_store
from app.utils.tool_helpers import logger


def load_knowledge_base_documents(
    kb_dir: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """
    Load and parse all CMS policy documents from knowledge_base/cms directory.
    """
    if kb_dir is None:
        kb_dir = Path(__file__).resolve().parent.parent.parent.parent / "knowledge_base" / "cms"

    documents: List[Dict[str, Any]] = []

    if not kb_dir.exists():
        logger.warning("Knowledge base directory %s does not exist.", kb_dir)
        return documents

    for file_path in sorted(kb_dir.glob("*.json")):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            doc_id = data.get("document_id", file_path.stem)
            doc_title = data.get("document_title", "")
            doc_type = data.get("document_type", "CMS Guidance")
            org = data.get("organization", "CMS")
            source = data.get("source", "CMS Policy")
            url = data.get("url", "")
            effective_date = data.get("effective_date", "")
            pub_date = data.get("publication_date", "")
            jurisdiction = data.get("jurisdiction", "National")
            procedure = data.get("procedure", "")
            policy_type = data.get("policy_type", "Coverage Policy")

            sections = data.get("sections", [])
            for idx, sec in enumerate(sections):
                sec_name = sec.get("section_name", f"Section {idx+1}")
                sec_num = sec.get("section_number", f"Sec {idx+1}")
                page = sec.get("page", idx + 1)
                text = sec.get("text", "").strip()

                if not text:
                    continue

                chunk_id = f"{doc_id}_{sec_num.replace(' ', '_')}_{idx}"
                documents.append({
                    "id": chunk_id,
                    "text": text,
                    "metadata": {
                        "document_id": doc_id,
                        "document_title": doc_title,
                        "document_type": doc_type,
                        "organization": org,
                        "source": source,
                        "url": url,
                        "effective_date": effective_date,
                        "publication_date": pub_date,
                        "jurisdiction": jurisdiction,
                        "procedure": procedure,
                        "policy_type": policy_type,
                        "section_name": sec_name,
                        "section_number": sec_num,
                        "page": int(page),
                    },
                })
        except Exception as exc:
            logger.error("Error reading document %s: %s", file_path, exc)

    logger.info("Loaded %d sections from %s", len(documents), kb_dir)
    return documents


def ingest_cms_knowledge_base(
    persist_directory: Optional[str] = None,
    collection_name: str = "cms_knowledge_base",
) -> int:
    """
    Ingest CMS documents into persistent Vector Store.
    """
    persist_dir = persist_directory or settings.chroma_persist_directory
    os.makedirs(persist_dir, exist_ok=True)

    logger.info("Initializing Vector Store at %s", persist_dir)
    vector_store = get_vector_store(
        collection_name=collection_name,
        persist_directory=persist_dir,
    )

    documents = load_knowledge_base_documents()
    if not documents:
        logger.warning("No documents found to ingest.")
        return 0

    ids = [d["id"] for d in documents]
    texts = [d["text"] for d in documents]
    metas = [d["metadata"] for d in documents]

    # Generate embeddings
    ef = get_embedding_function()
    embeddings = ef(texts)

    # Upsert documents into Vector Store
    vector_store.upsert(
        ids=ids,
        documents=texts,
        metadatas=metas,
        embeddings=embeddings,
    )

    # Cache indexed documents for fast BM25 keyword matching
    cache_file = Path(persist_dir) / "indexed_corpus.json"
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(documents, f, indent=2)

    logger.info(
        "Successfully indexed %d chunks into Vector Store collection '%s'.",
        len(documents),
        collection_name,
    )
    return len(documents)


if __name__ == "__main__":
    count = ingest_cms_knowledge_base()
    print(f"Ingestion complete: {count} authoritative CMS document chunks indexed.")
