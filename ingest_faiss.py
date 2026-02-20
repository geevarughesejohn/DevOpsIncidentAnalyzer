import os
import json
from glob import glob

from langchain.docstore.document import Document
from langchain_community.vectorstores import FAISS
from logging_config import get_logger
from model_config import get_embeddings

# ==========================
# CONFIG
# ==========================

DATA_PATH = "data"
FAISS_INDEX_PATH = "faiss_index"

# Azure config (set as env variables)
# export AZURE_OPENAI_API_KEY=...
# export AZURE_OPENAI_ENDPOINT=...

embeddings = get_embeddings()
logger = get_logger(__name__)


def load_documents():
    documents = []
    json_file_paths = glob(f"{DATA_PATH}/**/*.json", recursive=True)
    extensionless_paths = [
        path
        for path in glob(f"{DATA_PATH}/**/*", recursive=True)
        if os.path.isfile(path) and "." not in os.path.basename(path)
    ]
    file_paths = sorted(set(json_file_paths + extensionless_paths))
    logger.info("Discovered data files | files=%s", len(file_paths))

    for file_path in file_paths:
        logger.debug("Loading document file | path=%s", file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

            if isinstance(data, list):
                for item in data:
                    documents.append(
                        Document(
                            page_content=item["content"],
                            metadata=item.get("metadata", {})
                        )
                    )
            else:
                documents.append(
                    Document(
                        page_content=data["content"],
                        metadata=data.get("metadata", {})
                    )
                )

    return documents


def ingest():
    logger.info("Ingestion started | data_path=%s index_path=%s", DATA_PATH, FAISS_INDEX_PATH)
    docs = load_documents()
    logger.info("Documents loaded | count=%s", len(docs))
    if not docs:
        raise ValueError(
            f"No documents loaded from '{DATA_PATH}'. "
            "Ensure files are valid JSON and present under the data directory."
        )

    vectorstore = FAISS.from_documents(docs, embeddings)
    vectorstore.save_local(FAISS_INDEX_PATH)

    logger.info("FAISS index created successfully | path=%s", FAISS_INDEX_PATH)


if __name__ == "__main__":
    ingest()
