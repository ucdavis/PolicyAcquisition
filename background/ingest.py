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
import tempfile
from typing import List
import uuid

from pdf2image import convert_from_path
import requests
from db import IndexAttempt, IndexStatus, IndexedDocument, Source
from logger import setup_logger
from store import vectorize_text
from policy_details import PolicyDetails
from pypdf import PdfReader
import pytesseract

logger = setup_logger()

user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


# download the document and return a path to the downloaded file
def download_pdf(url: str, dir: str) -> str:
    headers = {"User-Agent": user_agent}
    response = requests.get(url, headers=headers, allow_redirects=True)
    response.raise_for_status()

    unique_filename = f"{uuid.uuid4()}.pdf"
    pdf_path = os.path.join(dir, unique_filename)

    with open(pdf_path, "wb") as file:
        file.write(response.content)

    return pdf_path


def calculate_file_hash(file_path: str) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as afile:
        buf = afile.read()
        hasher.update(buf)
    return hasher.hexdigest()


def extract_text_from_image(input_path):
    images = convert_from_path(
        input_path, 300
    )  # 300 DPI, play with larger values for better quality

    text = ""
    for image in images:
        text += pytesseract.image_to_string(image) or ""

    return text


def extract_text_from_pdf(input_path: str) -> str:
    try:
        with open(input_path, "rb") as file:
            pdf = PdfReader(file)
            text = ""
            for page in pdf.pages:
                text += (
                    page.extract_text() or ""
                )  # Adding a fallback of empty string if None is returned

            # if text is empty, then we might have a scanned pdf -- try to extract text using OCR
            if not text:
                text = extract_text_from_image(input_path)

            return text
    except Exception as e:
        logger.error(f"Error extracting text from {input_path}: {e}")


def get_document_by_url(url: str) -> IndexedDocument:
    return IndexedDocument.objects(url=url).first()


def ingest_documents(source: Source, policies: List[PolicyDetails]) -> IndexAttempt:
    start_time = datetime.now(timezone.utc)
    num_docs_indexed = 0
    num_new_docs = 0

    with tempfile.TemporaryDirectory() as temp_dir:
        for policy in policies:
            # TODO: for now it's all PDF, but we'll need to handle other file types

            # download the document
            # calculate the file hash
            # check if it exists in the database
            # extract the text
            # vectorize the text
            # save the document to elastic search
            # save the document to the database

            # Create a temporary directory to work within
            with tempfile.TemporaryDirectory() as temp_dir:
                pdf_path = download_pdf(policy.url, temp_dir)
                pdf_hash = calculate_file_hash(pdf_path)

                document = get_document_by_url(policy.url)

                # if the document exists and hasn't changed, skip
                if document and document.metadata.get("hash") == pdf_hash:
                    logger.info(f"Document {policy.url} has not changed, skipping")
                    continue

                extracted_text = extract_text_from_pdf(pdf_path)

                if not extracted_text:
                    logger.warning(f"No text extracted from {pdf_path}")
                    continue

                # add some metadata
                vectorized_document = policy.to_vectorized_document(extracted_text)
                vectorized_document.metadata.hash = pdf_hash
                vectorized_document.metadata.content_length = len(extracted_text)
                vectorized_document.metadata.scope = source.name

                result = vectorize_text(vectorized_document)

                if result:
                    logger.info(f"Successfully indexed document {policy.url}")
                    num_docs_indexed += 1
                    if not document:
                        # new doc we have never seen, create it
                        num_new_docs += 1
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

        logger.info(f"Indexed {num_docs_indexed} documents from source {source.name}")

        end_time = datetime.now(timezone.utc)

        ## TODO: somewhere remove old documents that are no longer in the source

        # not a real attempt but useful for returning the results. not sure the best way to handle this -- maybe pass in the attempt object?
        index_attempt = IndexAttempt(
            num_docs_indexed=num_docs_indexed,
            num_new_docs=num_new_docs,
            source_id=source._id,
            start_time=start_time,
            end_time=end_time,
            duration=(end_time - start_time).total_seconds(),
            status=IndexStatus.SUCCESS,
        )

        return index_attempt
