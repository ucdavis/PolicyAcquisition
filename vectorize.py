## Take all text files in the "content" output folder, split and vectorize them, then push to Elasticsearch

import logging
import os
import json
import time
from dotenv import load_dotenv
import hashlib
from elasticsearch import Elasticsearch

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_elasticsearch import ElasticsearchStore
from langchain_openai import OpenAIEmbeddings

load_dotenv()  # Load environment variables

file_storage_path_base = os.getenv("FILE_STORAGE_PATH", "./output")

logger = logging.getLogger(__name__)

API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    print("OpenAI API key is required")
    exit(1)

# Setup for Elasticsearch
ELASTIC_URL = os.getenv("ELASTIC_URL", "http://127.0.0.1:9200")
ELASTIC_WRITE_USERNAME = os.getenv("ELASTIC_WRITE_USERNAME", "")
ELASTIC_WRITE_PASSWORD = os.getenv("ELASTIC_WRITE_PASSWORD", "")
ELASTIC_INDEX = os.getenv("ELASTIC_INDEX", "policy_vectorstore_dev")

# Create our elastic client
es_client = Elasticsearch(hosts=[ELASTIC_URL], basic_auth=(ELASTIC_WRITE_USERNAME, ELASTIC_WRITE_PASSWORD), max_retries=10, retry_on_timeout=True)

# might want to play with `text-embedding-3-small` later
embedding = OpenAIEmbeddings(model="text-embedding-3-large")

# revisions are classified as "Resource" but we don't want to include them in the search
ignoredClassifications = ["Resource"]


def get_folders(base_path):
    """
    Gets non-hidden folders in the `base_path` directory and subdirectories
    Return a dictionary with the folder names as keys and the file paths as values
    """
    folders = {}
    for root, dirs, files in os.walk(base_path):
        for dir in dirs:
            if not dir.startswith("."):
                folders[dir] = os.path.join(root, dir)
    return folders


def load_documents_from_folder(folder_path, update_progress):
    """
    Reads the metadata.json from the folder path and then reads the file contents
    into a new "content" key in the metadata dictionary for each file. Also adds a hash key.

    Args:
        folder_path: The path to the folder containing the metadata.json and content files.
        update_progress: A callback function to update the progress of the vectorization.

    Returns:
        A list of dictionaries, each containing the metadata and content of a file.
    """

    update_progress(f"Loading documents from {folder_path}")

    metadata_path = os.path.join(folder_path, "metadata.json")
    if not os.path.exists(metadata_path):
        update_progress(f"metadata.json not found in {folder_path}. Skipping")
        return []

    with open(metadata_path, "r") as file:
        file_data = json.load(file)

    # file_data is an array of dictionaries, let's loop through and read the content
    for data in file_data:
        content_path = os.path.join(
            folder_path, data["filename"] + ".txt"
        )  # always text files in content
        if os.path.exists(content_path):
            md5_hash = hashlib.md5()
            with open(content_path, "r") as file:
                data["content"] = file.read()
                text = data["content"].encode("utf-8")
                md5_hash.update(text)
                data["hash"] = md5_hash.hexdigest()
        else:
            pass
            logger.error(f"Content file {content_path} not found")
            # update_progress(f"Content file {content_path} not found")

    return file_data


def process_folders(folders, update_progress):
    """
    Processes the folders and their contents, then pushes the vectorized data to Elasticsearch.

    Args:
        folders: A dictionary of folder names and paths.
        update_progress: A callback function to update the progress of the vectorization.
    """
    real_index_name = "policy_vectorstore_" + str(int(time.time()))

    for folder_name, folder_path in folders.items():
        update_progress(f"Processing {folder_name}")
        documents = load_documents_from_folder(folder_path, update_progress)

        documents_to_index = []
        for document in documents:
            ## TODO:
            ## Filter out ignored classifications
            ## Turn into documents for langchain to split
            ## vectorize and push into ES, probably in batches (200 at a time seems ok)
            # print(document)

            # Make sure document has content
            if "content" in document:
                pass
            else:
                logger.error(f"Document {document['filename']} has no content")
                continue

            # skip if the document has an ignored classification
            if "classifications" in document:
                if any(
                    c in ignoredClassifications for c in document["classifications"]
                ):
                    continue

            # turn into a document for langchain to split
            metadata = document.copy()
            metadata.pop("content")  # remove content from metadata

            # add in scope
            metadata["scope"] = folder_name

            langchain_document = Document(
                page_content=document["content"], metadata=metadata
            )

            documents_to_index.append(langchain_document)

        # now we have a bunch of documents to index for this folder

        # split - TODO: play with chunk size and overlap
        text_splitter = RecursiveCharacterTextSplitter()

        splitDocs = text_splitter.split_documents(documents_to_index)

        update_progress(
            f"Vectorizing and pushing to Elasticsearch {len(splitDocs)} documents in {folder_name}"
        )

        # split into chunks of 200
        chunk_size = 200
        for i in range(0, len(splitDocs), chunk_size):
            update_progress(
                f"Processing chunk {i} to {i+chunk_size} of {len(splitDocs)} in {folder_name}"
            )
            ElasticsearchStore.from_documents(
                splitDocs[i : i + chunk_size],
                embedding,
                index_name=real_index_name,
                es_connection=es_client,
            )

        update_progress(f"Finished processing {folder_name}")
    
    update_progress(f"Finished processing all folders. New index is {real_index_name}. Swapping aliases...")

    create_and_update_alias(real_index_name)

    update_progress(f"Alias updated to {real_index_name}")


def create_and_update_alias(index_name):
    """
    We are going to swap the alias from the current index to the new index given by `index_name`

    Args:
        index_name: The name of the new index to swap to.
    """

    # Step 0: Assume the index is already created (since langchain does that for us)

    # Create our elastic client

    # Find all indexes the alias points to currently
    alias_exists = es_client.indices.exists_alias(name=ELASTIC_INDEX)

    # setup actions to perform
    actions = []

    actions.append(
        {
            "add": {
                "index": index_name,
                "alias": ELASTIC_INDEX,
            }
        }
    )

    indexes_to_remove = []

    if alias_exists:
        # Get all indexes the alias points to
        indexes = es_client.indices.get_alias(name=ELASTIC_INDEX)

        for index in indexes:
            if index != index_name:
                indexes_to_remove.append(index)
            actions.append(
                {
                    "remove": {
                        "index": index,
                        "alias": ELASTIC_INDEX,
                    }
                }
            )
    
    # Execute -- update the alias (remove from old indices and add to new index)
    es_client.indices.update_aliases(body={"actions": actions})

    # Delete the old indexes
    for index in indexes_to_remove:
        es_client.indices.delete(index=index)


def vectorize(update_progress):
    """
    Vectorizes the text files in the content folder and pushes them to Elasticsearch
    Args:
        update_progress: A callback function to update the progress of the vectorization.
    """

    all_folders = get_folders(os.path.join(file_storage_path_base, "content"))

    update_progress(f"Found {len(all_folders)} folders")

    process_folders(all_folders, update_progress)

    update_progress("Finished vectorizing and pushing to Elasticsearch")