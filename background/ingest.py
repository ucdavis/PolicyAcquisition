## This will ingest documents from the provided source from downloading to vectorizing and saving to elastic
# Strategy:
# - One at a time, download the document from the source
# - Calculate the file hash and check if it already exists in the database
# - If it exists and hasn't been changed, quit
# - If it exists and has been changed, or doesn't exist, continue to next step
# - Extract the text from the document
# - Vectorize the text
# - Save the document to elastic search
# - Update the source's last_updated field or create it if it doesn't exist

from datetime import datetime, timezone
import hashlib
import os
import random
import tempfile
import time
from typing import List, Tuple
import uuid

import requests
from background.extract import (
    cleanup_extracted_text,
    extract_text_from_policy_file,
)
from db import IndexedDocument, Source
from logger import log_memory_usage, setup_logger
from store import vectorize_text
from models.policy_details import PolicyDetails, VectorDocument

logger = setup_logger()

user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


class IngestResult:
    def __init__(
        self,
        num_docs_indexed,
        num_new_docs,
        source_id,
        start_time,
        end_time,
        duration,
    ):
        self.num_docs_indexed = num_docs_indexed
        self.num_new_docs = num_new_docs
        self.source_id = source_id
        self.start_time = start_time
        self.end_time = end_time
        self.duration = duration


def request_with_retry(url, retries=5, backoff_factor=1, **kwargs):
    """
    Sends a GET request to the specified URL with retry mechanism.

    Args:
        url (str): The URL to send the request to.
        retries (int, optional): The number of retries to attempt. Defaults to 5.
        backoff_factor (int, optional): The backoff factor for exponential backoff. Defaults to 1.
        **kwargs: Additional keyword arguments to pass to the requests.get() function.

    Returns:
        requests.Response or None: The response object if the request is successful, None otherwise.
    """
    for attempt in range(retries):
        try:
            response = requests.get(url, **kwargs)
            if response.status_code == 200:
                return response
            else:
                logger.warning(
                    f"Request to {url} returned status code {response.status_code} on attempt {attempt + 1}"
                )
        except requests.exceptions.RequestException as e:
            logger.warning(
                f"Request to {url} failed on attempt {attempt + 1} with exception: {e}"
            )

        # If we are here, that means the request failed. We wait before retrying.
        wait_time = backoff_factor * (2**attempt)
        logger.info(f"Retrying request to {url} in {wait_time} seconds...")
        time.sleep(wait_time)

    # If we exit the loop without returning, it means we've exhausted all attempts
    logger.error(f"Failed to fetch {url} after {retries} attempts")
    return None


def wait_before_next_request():
    time.sleep(random.uniform(1, 3))  # Sleep for 1 to 3 seconds


def download_policy(url: str, dir: str) -> str:
    """
    Download a policy from the given URL and save it to the specified directory.
    Will determine if file is PDF or text file and add the appropriate extension.
    """
    headers = {"User-Agent": user_agent}
    response = request_with_retry(
        url, headers=headers, allow_redirects=True, timeout=60
    )

    if not response:
        logger.error(f"Failed to download {url}")
        return None

    response.raise_for_status()

    file_type = "txt"  # default to text

    # check if the response is a PDF
    if "Content-Type" in response.headers:
        content_type = response.headers["Content-Type"]
        if "application/pdf" in content_type:
            file_type = "pdf"

    unique_filename = f"{uuid.uuid4()}.{file_type}"

    file_path = os.path.join(dir, unique_filename)

    with open(file_path, "wb") as file:
        file.write(response.content)

    return file_path


def calculate_file_hash(file_path: str) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as afile:
        buf = afile.read()
        hasher.update(buf)
    return hasher.hexdigest()


def get_document_by_url(url: str) -> IndexedDocument:
    return IndexedDocument.objects(url=url).first()


def ingest_policies(source: Source, policies: List[PolicyDetails]) -> IngestResult:
    start_time = datetime.now(timezone.utc)
    num_docs_indexed = 0
    num_new_docs = 0

    with tempfile.TemporaryDirectory() as temp_dir:
        for policy in policies:
            logger.info(f"Processing policy {policy.url}")
            log_memory_usage(logger)

            # download the policy at the given url
            # calculate the file hash
            # check if it exists in the database
            # extract the text
            # vectorize the text
            # save the document to elastic search
            # save the document to the database

            if not policy:
                logger.warning(f"Policy is None, skipping")
                continue

            local_policy_path = download_policy(policy.url, temp_dir)

            if not local_policy_path:
                logger.error(f"Failed to download pdf at {policy.url}. ")
                continue

            policy_file_hash = calculate_file_hash(local_policy_path)

            document = get_document_by_url(policy.url)

            # if the document exists and hasn't changed, skip
            if document and document.metadata.get("hash") == policy_file_hash:
                logger.info(f"Document {policy.url} has not changed, skipping")
                # if we skip a document, let's wait a bit to avoid rate limiting
                wait_before_next_request()
                continue

            extracted_text = extract_text_from_policy_file(local_policy_path, policy)

            if not extracted_text:
                logger.warning(f"No text extracted from {local_policy_path}")
                continue

            extracted_text = cleanup_extracted_text(extracted_text)

            # add some metadata
            vectorized_document = policy.to_vectorized_document(extracted_text)
            vectorized_document.metadata.hash = policy_file_hash
            vectorized_document.metadata.content_length = len(extracted_text)
            vectorized_document.metadata.scope = source.name

            # if we haven't seen this document before, increment the count
            num_new_docs += 1 if not document else 0
            num_docs_indexed += 1  # record the indexing either way

            result = vectorize_text(vectorized_document)

            update_document(
                source,
                policy,
                document,
                vectorized_document,
                result,
            )

        logger.info(f"Indexed {num_docs_indexed} documents from source {source.name}")

        end_time = datetime.now(timezone.utc)

        ## TODO: somewhere remove old documents that are no longer in the source

        return IngestResult(
            num_docs_indexed=num_docs_indexed,
            num_new_docs=num_new_docs,
            source_id=source._id,
            start_time=start_time,
            end_time=end_time,
            duration=(end_time - start_time).total_seconds(),
        )


def update_document(
    source: Source,
    policy: PolicyDetails,
    document: IndexedDocument,
    vectorized_document: VectorDocument,
    result: dict,
):
    if result:
        logger.info(f"Successfully indexed document {policy.url}")
        if not document:
            # new doc we have never seen, create it
            document = IndexedDocument(
                url=policy.url,
                metadata=vectorized_document.metadata.to_dict(),
                title=policy.title,
                filename=policy.filename,
                last_updated=datetime.now(timezone.utc),
                source_id=source._id,
            )
        else:
            # existing doc so just update
            document.metadata = vectorized_document.metadata.to_dict()
            document.title = policy.title
            document.filename = policy.filename
            document.last_updated = datetime.now(timezone.utc)

        document.save()

    else:
        logger.error(f"Failed to index document {policy.url}")


def ingest_kb_documents(
    source: Source, policy_details_with_text: List[Tuple[PolicyDetails, str]]
) -> IngestResult:
    # KB is a special case, we already have the content
    # eventually it'd be nice to either scrape the site or get API access instead
    start_time = datetime.now(timezone.utc)
    num_docs_indexed = 0
    num_new_docs = 0

    for policy, text in policy_details_with_text:
        logger.info(f"Processing document {policy.url}")
        log_memory_usage(logger)

        hash = hashlib.sha256(text.encode()).hexdigest()

        document = get_document_by_url(policy.url)

        # if the document exists and hasn't changed, skip
        if document and document.metadata.get("hash") == hash:
            logger.info(f"Document {policy.url} has not changed, skipping")
            continue

        if not text:
            logger.warning(f"No text extracted from {policy.url}")
            continue

        # add some metadata
        vectorized_document = policy.to_vectorized_document(text)
        vectorized_document.metadata.hash = hash
        vectorized_document.metadata.content_length = len(text)
        vectorized_document.metadata.scope = source.name

        # if we haven't seen this document before, increment the count
        num_new_docs += 1 if not document else 0
        num_docs_indexed += 1  # record the indexing either way

        result = vectorize_text(vectorized_document)

        update_document(
            source,
            policy,
            document,
            vectorized_document,
            result,
        )

    logger.info(f"Indexed {num_docs_indexed} documents from source {source.name}")

    end_time = datetime.now(timezone.utc)

    ## TODO: somewhere remove old documents that are no longer in the source

    return IngestResult(
        num_docs_indexed=num_docs_indexed,
        num_new_docs=num_new_docs,
        source_id=source._id,
        start_time=start_time,
        end_time=end_time,
        duration=(end_time - start_time).total_seconds(),
    )
