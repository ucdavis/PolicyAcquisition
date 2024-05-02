from datetime import datetime
import json
import logging
import os
from typing import List
from urllib.parse import urljoin
from dotenv import load_dotenv

import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

from policy_details import PolicyDetails
from shared import get_driver

load_dotenv()  # This loads the environment variables from .env

logger = logging.getLogger(__name__)

file_storage_path_base = os.getenv("FILE_STORAGE_PATH", "./output")

## UC Davis Academic Affairs Policies are on `https://academicaffairs.ucdavis.edu/`
## Covers APM (Academic Personnel Manual), plus other policies that we may want to include
base_url = "https://academicaffairs.ucdavis.edu/"

user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


#### TODO: Refactor this since we use it in multiple places
def download_pdf(url, directory, filename):
    path = os.path.join(directory, filename)
    # if we already have the file, skip it
    if os.path.exists(path):
        logger.info(f"Already have {filename}")
        return

    headers = {"User-Agent": user_agent}
    response = requests.get(url, headers=headers, allow_redirects=True)
    with open(path, "wb") as file:
        file.write(response.content)


def get_apm_links(driver, url):
    policy_link_info_list: List[PolicyDetails] = []

    # get the page and find all PDF links
    driver.get(url)

    # wait for the page to load
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "block-sitefarm-one-content"))
        )
    except Exception as e:
        logger.error(f"Error waiting for page to load: {e}")
        raise  # re-raise the exception

    soup = BeautifulSoup(driver.page_source, "html.parser")

    # main content (no headers or sidebar, etc)
    content = soup.find(id="block-sitefarm-one-content")

    # find all 'a' tags within the content
    links = content.find_all("a")

    for link in links:
        href = link.get("href")
        title = link.get_text().strip()

        # skip if no href or title
        if not href or not title:
            continue

        if href and href.endswith(".pdf"):
            logger.info(f"Found PDF link: {href}")
            # we don't have much info here
            policy_link_info_list.append(PolicyDetails(title, href))

    return policy_link_info_list


### Download files for the APM
def download_apm(driver, update_progress):
    # table of contents
    apm_url = urljoin(base_url, "apm/apm-toc")

    update_progress("Starting APM download process...")

    policy_link_info_list = get_apm_links(driver, apm_url)

    #### TODO: this code is similar to other download functions, should be refactored
    # create a directory to save the pdfs
    directory = os.path.join(
        file_storage_path_base, "./docs/ucd/academicaffairs/ucdapm"
    )
    os.makedirs(directory, exist_ok=True)

    # save the list of policies with other metadata to a JSON file for later
    policy_details_json = os.path.join(directory, "metadata.json")

    # delete the file if it exists
    try:
        os.remove(policy_details_json)
    except OSError:
        pass

    with open(os.path.join(directory, "metadata.json"), "w") as f:
        json.dump([policy.__dict__ for policy in policy_link_info_list], f, indent=4)

    total_links = len(policy_link_info_list)

    # provide 20 status updates during the process
    total_updates = 20

    # Calculate the frequency of updates
    update_frequency = total_links // total_updates

    # iterate through the list of links and download the pdfs
    for i, link_info in enumerate(policy_link_info_list):
        url = link_info.url
        title = link_info.title
        pdf_filename = f"{link_info.filename}.pdf"

        if update_frequency > 0 and (i + 1) % update_frequency == 0:
            progress_percentage = round(((i + 1) / total_links) * 100, 2)
            update_progress(
                f"{progress_percentage:.2f}% - Downloading {title} from {url} as {pdf_filename} - {i+1} of {total_links}"
            )

        logger.info(f"Downloading {title} from {url} as {pdf_filename}")
        download_pdf(url, directory, pdf_filename)

    # create a JSON file with run details
    with open(os.path.join(directory, "run_details.json"), "w") as f:
        completed_date = datetime.now().isoformat()
        json.dump(
            {
                "total_policies": total_links,
                "status": "completed",
                "completed_date": completed_date,
            },
            f,
            indent=4,
        )

    update_progress("Complete: academic affairs download process")


#### Main function
#### This will read all of the policies, store their URLs in metadata.json, and then store each in a file
#### Note: This will only add new policies to the folder, it will not overwrite existing or delete missing
def download_academic_affairs(update_progress):
    """Download all UCOP policies and save them to the file storage path."""
    driver = get_driver()

    update_progress("Starting academic affairs download process...")

    download_apm(driver, update_progress)


if __name__ == "__main__":
    download_academic_affairs(print)
