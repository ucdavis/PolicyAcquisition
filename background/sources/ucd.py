from urllib.parse import urljoin
from background.logger import setup_logger
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from typing import List
import re
import os
import time

from background.models.policy_details import PolicyDetails

load_dotenv()  # This loads the environment variables from .env

logger = setup_logger()

file_storage_path_base = os.getenv("FILE_STORAGE_PATH", "./output")

## UCD Policies are on `https://ucdavispolicy.ellucid.com`
## There are several different binders each with their own set of policies
base_url = "https://ucdavispolicy.ellucid.com"
home_url_minus_binder = f"{base_url}/manuals/binder"

# make a dictionary of the different binders
binders = {
    "11": "ucdppm",
    "13": "ucdppsm",
    "243": "ucdinterim",
    "15": "ucddelegation",
}

# never navigate into these folders
ignore_folders = ["Parent Directory"]
# tag these folders as revision history
# revision_folders = ["PPM Revision History", "PPSM Revision History"]

user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def get_ucd_policy_binders():
    """Get the list of policy binders from the UCD Ellucid site."""
    return [(binder, f"{home_url_minus_binder}/{binder}") for binder in binders]


def get_ucd_policy_links(driver, url):
    # policy links are to the policy page, not the actual PDF
    # we need to go to each page and get the PDF link from the iframe
    policy_links = get_nested_links_selenium(driver, url)

    for policy in policy_links:
        pdf_src, _ = get_iframe_src_and_title(driver, policy.url)

        if pdf_src:
            pdf_url = urljoin(base_url, pdf_src)
            policy.url = pdf_url

    return policy_links


def sanitize_filename(filename):
    """Sanitize the filename by removing or replacing invalid characters."""
    return re.sub(r'[\\/*?:"<>|]', "", filename)


def get_iframe_src_and_title(driver, url):
    driver.get(url)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "document-viewer"))
        )
    except Exception as e:
        logger.error(f"Error waiting for iframe: {e}")
        return None, None

    soup = BeautifulSoup(driver.page_source, "html.parser")
    iframe = soup.find(id="document-viewer")
    title_element = soup.find(class_="doc_title")
    title = title_element.get_text(strip=True) if title_element else "Untitled"
    return (iframe["src"] if iframe else None, title)


# simple returns all the folder or file links on a page
def get_links_selenium(driver, url):
    driver.get(url)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "browse-link"))
        )
    except Exception as e:
        logger.error(f"Error waiting for content: {e}")
        return []

    soup = BeautifulSoup(driver.page_source, "html.parser")

    return get_policy_details_from_table(soup)


def get_policy_details_from_table(soup: BeautifulSoup):
    """
    Extracts policy details from a table in the given BeautifulSoup object.

    Args:
        soup (BeautifulSoup): The BeautifulSoup object representing the HTML page.

    Returns:
        List[PolicyDetails]: A list of PolicyDetails objects containing the extracted policy details.
    """
    all_links: List[PolicyDetails] = []

    # main table is div with class="ag-center-cols-container"
    # inside are divs role="row" and we want to iterate over them
    rows = soup.select("div.ag-center-cols-container div[role=row]")

    for row in rows:
        policyRow = PolicyDetails()

        # go through the cells in the row, each are divs with role="gridcell"
        # we want the `col-id` and the text inside the div
        columns = row.select("div[role=gridcell]")

        for column in columns:
            col_id = column["col-id"]
            text = column.text.strip()

            if col_id == "approvedOn":
                policyRow.effective_date = text
                policyRow.issuance_date = text
            elif col_id == "keywords":
                policyRow.keywords = [keyword.strip() for keyword in text.split(",")]
            elif col_id == "standardReferences":
                policyRow.subject_areas = [area.strip() for area in text.split(";")]
            elif col_id == "documentClassifications":
                policyRow.classifications = [
                    classification.strip() for classification in text.split(",")
                ]
            elif col_id == "element":
                # this is the actual document link
                # we want to look inside this column and pull out the div.browse-link -> a tag
                a = column.select_one("div.browse-link a")
                policyRow.title = a.text.strip()
                policyRow.url = urljoin(base_url, a["href"])
                policyRow.filename = sanitize_filename(policyRow.title)

        all_links.append(policyRow)

    return all_links


# returns file links and can go into folders
# file links include href and title
def get_nested_links_selenium(driver, url):
    driver.get(url)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "browse-link"))
        )
    except Exception as e:
        logger.error(f"Error waiting for content: {e}")
        return []

    # now change the select.page-size element to 100
    select = driver.find_element(By.CLASS_NAME, "page-size")
    select.click()
    select.send_keys("100")

    # now we want to add all the columns, so we need to click the column button and then click all the checkboxes
    column_button = driver.find_element(By.CLASS_NAME, "ag-side-button")
    column_button.click()

    WebDriverWait(driver, 3).until(
        EC.element_to_be_clickable((By.CLASS_NAME, "ag-column-tool-panel-column"))
    )

    checkbox_spans = driver.find_elements(By.CLASS_NAME, "ag-column-tool-panel-column")

    # click all the checkboxes
    for cb in checkbox_spans:
        cb.click()

    # wait for the page to update. It's pretty fast to 3 seconds should be enough
    time.sleep(3)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    file_links: List[PolicyDetails] = []

    # first get all links on the homepage of the binder
    all_links: List[PolicyDetails] = get_policy_details_from_table(soup)

    # links will either be a folder or a document
    # folders will start with `/manuals/binder` and documents will start with `/documents`
    # if we find a folder, we need to go into it and get the documents
    for link in all_links:
        # if the folder is in the ignore list, skip it
        if link.title in ignore_folders:
            continue

        if "/manuals/binder" in link.url:
            nested_links = get_links_selenium(driver, link.url)

            # occasionally we can go 3 levels deep
            for nested_link in nested_links:
                if nested_link.title in ignore_folders:
                    continue

                if "/manuals/binder" in nested_link.url:
                    deep_nested_links = get_links_selenium(driver, nested_link.url)

                    for deep_nested_link in deep_nested_links:
                        if deep_nested_link.title in ignore_folders:
                            continue

                        if "/documents" in deep_nested_link.url:
                            file_links.append(deep_nested_link)
                else:
                    file_links.append(nested_link)
        else:
            file_links.append(link)

    return file_links
