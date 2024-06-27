import os
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult, AnalyzeDocumentRequest
from pypdf import PdfReader

from background.logger import setup_logger

logger = setup_logger()

endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
credential = AzureKeyCredential(os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY"))
document_intelligence_client = DocumentIntelligenceClient(endpoint, credential)


def extract_text_from_unreadable_doc(doc_url: str) -> str | None:
    """
    Extract text from a document that is not readable by the
    pypdf library. This could be due to the document being
    a scanned PDF or an image file.

    Uses Azure's Document Intelligence service to extract text.
    """
    try:
        logger.info(f"Analyzing document {doc_url} for OCR text extraction")

        poller = document_intelligence_client.begin_analyze_document(
            "prebuilt-read", AnalyzeDocumentRequest(url_source=doc_url)
        )
        result: AnalyzeResult = poller.result()

        text = ""

        for page in result.pages:
            for line in page.lines:
                text += line.content + "\n"

        return text
    except Exception as e:
        logger.error(f"Error analyzing document {doc_url}: {e}")
        return None


def extract_text_from_pdf(input_path: str, original_doc_url: str) -> str:
    """
    Extract text from a PDF file. If the text is empty, then
    we might have a scanned PDF -- try to extract text using OCR.
    """
    try:
        logger.info(f"Extracting text from {original_doc_url}")
        with open(input_path, "rb") as file:
            pdf = PdfReader(file)
            text = ""
            for page in pdf.pages:
                text += (
                    page.extract_text() or ""
                )  # Adding a fallback of empty string if None is returned

            # if text is empty, then we might have a scanned pdf -- try to extract text using OCR
            if not text:
                logger.info(f"Extracting text using OCR from {original_doc_url}")
                text = extract_text_from_unreadable_doc(original_doc_url)

            return text
    except Exception as e:
        logger.error(f"Error extracting text from {original_doc_url}: {e}")
