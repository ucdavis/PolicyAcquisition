## Converts policy details to indexed documents

import os
from elasticsearch import Elasticsearch
from typing import List

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_elasticsearch import ElasticsearchStore
from langchain_openai import OpenAIEmbeddings
from langchain_core.embeddings import Embeddings

from logger import setup_logger
from policy_details import PolicyDetails, VectorDocument

logger = setup_logger()

API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    print("OpenAI API key is required")
    exit(1)

# Setup for Elasticsearch
ELASTIC_URL = os.getenv("ELASTIC_URL", "http://127.0.0.1:9200")
ELASTIC_WRITE_USERNAME = os.getenv("ELASTIC_WRITE_USERNAME", "")
ELASTIC_WRITE_PASSWORD = os.getenv("ELASTIC_WRITE_PASSWORD", "")
ELASTIC_INDEX = os.getenv("ELASTIC_INDEX", "policy_vectorstore_test")
ELASTIC_INDEX_FULLTEXT = os.getenv("ELASTIC_INDEX_FULLTEXT", "policy_fulltext_test")

# Create our elastic client
es_client = Elasticsearch(
    hosts=[ELASTIC_URL],
    basic_auth=(ELASTIC_WRITE_USERNAME, ELASTIC_WRITE_PASSWORD),
    max_retries=10,
    retry_on_timeout=True,
)

# might want to play with `text-embedding-3-small` later
# embedding = OpenAIEmbeddings(model="text-embedding-3-large")
embedding = OpenAIEmbeddings(model="text-embedding-3-small")  # small for testing

# revisions are classified as "Resource" but we don't want to include them in the search
ignoredClassifications = ["Resource"]


def vectorize_text(document: VectorDocument) -> dict:
    """
    Vectorize the text using a pre-trained model
    """
    # skip if the document has an ignored classification
    if document.metadata.classifications:
        if any(c in ignoredClassifications for c in document.metadata.classifications):
            logger.info(
                f"Skipping document {document.metadata.url} due to ignored classification"
            )
            return None

    # use langchain to split the text
    langchain_document = Document(
        page_content=document["content"], metadata=document.metadata.to_dict()
    )

    logger.info(f"Vectorizing document {document.metadata.url}")

    text_splitter = RecursiveCharacterTextSplitter(add_start_index=True)

    splitDocs = text_splitter.split_documents([langchain_document])

    # now push to Elasticsearch

    logger.info(f"Done indexing document {document.metadata.url}")

    # done, return our doc
    return document
