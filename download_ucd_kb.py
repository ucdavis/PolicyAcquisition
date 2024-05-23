from datetime import datetime
import json
import logging
import os
from dotenv import load_dotenv

from bs4 import BeautifulSoup

from policy_details import PolicyDetails

load_dotenv()  # This loads the environment variables from .env

logger = logging.getLogger(__name__)

file_storage_path_base = os.getenv("FILE_STORAGE_PATH", "./output")


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


def save_article_text_to_file(policy, text, directory):
    """Save the article text content to a file after stripping HTML."""
    # Use BeautifulSoup to strip HTML
    soup = BeautifulSoup(text, "html.parser")
    clean_text = soup.get_text(separator="\n")

    # Create a file with the sanitized filename
    filename = f"{policy.filename}.txt"
    with open(os.path.join(directory, filename), "w", encoding="utf-8") as f:
        f.write(clean_text)


#### Main function
#### This will read all of the KB articles, store their URLs in metadata.json, and then store each in a file
#### Note: This will only add new policies to the folder, it will not overwrite existing or delete missing
#### Note2: kb articles provided in JSON, so not actually downloaded
def download_ucd_kb(update_progress):
    """Download all UCD KB policies and save them to the file storage path."""

    directory = os.path.join(file_storage_path_base, "./docs/ucd/knowledgebase")

    update_progress("Starting UCD KB article extraction process...")

    # Load the JSON file of KB articles
    with open(
        os.path.join(directory, "kb_knowledge.json"),
        "r",
    ) as f:
        data = json.load(f)

    update_progress("Extracting policy details...")

    # Extract the articles array from the JSON data
    articles = data.get("records", [])

    # Create an array of PolicyDetails objects
    policy_details: list[PolicyDetails] = []

    for article in articles:
        policy = extract_policy_details(article)
        policy_details.append(policy)

        # Save the text content to a file
        text = article.get("text", "")
        save_article_text_to_file(policy, text, directory)

    update_progress("Saving metadata...")

    # save the list of policies with other metadata to a JSON file for later
    policy_details_json_path = os.path.join(directory, "metadata.json")

    # delete the file if it exists
    try:
        os.remove(policy_details_json_path)
    except OSError:
        pass

    with open(policy_details_json_path, "w") as f:
        json.dump([policy.__dict__ for policy in policy_details], f, indent=4)

    # create a JSON file with run details
    with open(os.path.join(directory, "run_details.json"), "w") as f:
        completed_date = datetime.now().isoformat()
        json.dump(
            {
                "total_policies": len(policy_details),
                "status": "completed",
                "completed_date": completed_date,
            },
            f,
            indent=4,
        )

    update_progress("UCD KB article extraction process completed.")


if __name__ == "__main__":
    download_ucd_kb(print)
