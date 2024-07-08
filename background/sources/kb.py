import json
import logging
from typing import List, Tuple
from dotenv import load_dotenv

from background.models.policy_details import PolicyDetails

load_dotenv()  # This loads the environment variables from .env

logger = logging.getLogger(__name__)

## Process KB links from the provided JSON file (kb_knowledge.json)
## This one is not automatically scraping the KB, we need to generate the new JSON file manually
## Eventually we are aiming to get API access so this should work for now

## To get the JSON file, go to service now -> knowledge -> published. Click on the "..." and export to JSON


def get_kb_details():
    # Load the JSON file of KB articles
    try:
        with open(
            "./background/data/kb_knowledge.json",
            "r",
        ) as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error("File kb_knowledge.json not found")
        return

    # Extract the articles array from the JSON data
    articles = data.get("records", [])

    # Create an array of PolicyDetails objects w/ text
    policy_details_with_text: List[Tuple[PolicyDetails, str]] = []

    for article in articles:
        policy = extract_policy_details(article)
        text = article.get("text", "")
        policy_details_with_text.append((policy, text))

    return policy_details_with_text


def extract_policy_details(article):
    """Extract policy details from an article."""
    title = article.get("short_description", "")
    url = (
        "https://kb.ucdavis.edu/?id=" + article.get("number", "")[2:]
    )  # remove the "KB" prefix
    effective_date = article.get("u_effective_date", None)
    issuance_date = article.get("sys_created_on", None)
    responsible_office = article.get("u_department_name", None)
    subject_areas = []
    keywords = article.get("meta", "").split(", ")
    classifications = []

    return PolicyDetails(
        title,
        url,
        effective_date,
        issuance_date,
        responsible_office,
        subject_areas,
        keywords,
        classifications,
    )
