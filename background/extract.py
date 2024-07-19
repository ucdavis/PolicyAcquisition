import os
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult, AnalyzeDocumentRequest
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pypdf import PdfReader

from background.logger import setup_logger
from policy_details import PolicyDetails

load_dotenv()

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


def extract_text_from_policy_file(input_path: str, policy: PolicyDetails) -> str:
    """
    Determine which extractor to use based on the file extension.
    """
    ext = os.path.splitext(input_path)[1].lower()

    if ext == ".pdf":
        return extract_text_from_pdf(input_path, policy)
    else:
        return extract_text_from_text_file(input_path, policy)


def extract_text_from_text_file(input_path: str, policy: PolicyDetails) -> str:
    """
    Extract text from a text file. Sounds simple.
    But we do want to check if it looks like HTML, and if so we should attempt to extract metadata too (like title)
    """

    try:
        with open(input_path, "r") as file:
            file_contents = file.read()
    except Exception as e:
        logger.error(f"Error extracting text from {policy.url}: {e}")
        return ""

    # Create a BeautifulSoup object
    soup = BeautifulSoup(file_contents, "lxml")

    # If the document does not have an 'html' tag, it is not a webpage
    if not soup.find("html"):
        return file_contents

    # Extract title (og:title or title tag)
    title = None
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = og_title["content"]
    else:
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.string

    # Extract keywords
    keywords = []
    meta_keywords = soup.find("meta", attrs={"name": "keywords"})
    if meta_keywords and meta_keywords.get("content"):
        keywords_content = meta_keywords["content"]
        keywords = [keyword.strip() for keyword in keywords_content.split(",")]

    # Extract content from <main> or <body>
    content = ""
    main_content = soup.find("main")
    if main_content:
        content = main_content.get_text(separator="\n").strip()
    else:
        body_content = soup.find("body")
        if body_content:
            content = body_content.get_text(separator="\n").strip()

    # modify the policy if we have a title or keywords
    if title:
        policy.title = title
    if keywords:
        policy.keywords = keywords

    # return the content
    return content


def extract_text_from_pdf(input_path: str, policy: PolicyDetails) -> str:
    """
    Extract text from a PDF file. If the text is empty, then
    we might have a scanned PDF -- try to extract text using OCR.
    """
    try:
        logger.info(f"Extracting text from {policy.url}")
        with open(input_path, "rb") as file:
            pdf = PdfReader(file)
            text = ""
            for page in pdf.pages:
                text += (
                    page.extract_text() or ""
                )  # Adding a fallback of empty string if None is returned

            # if text is empty, then we might have a scanned pdf -- try to extract text using OCR
            if not text:
                logger.info(f"Extracting text using OCR from {policy.url}")
                text = extract_text_from_unreadable_doc(policy.url)

            return text
    except Exception as e:
        logger.error(f"Error extracting text from {policy.url}: {e}")
