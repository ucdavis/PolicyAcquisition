import logging
import os
from datetime import datetime
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from selenium.common.exceptions import StaleElementReferenceException
import requests
import json
import os
from policy_details import PolicyDetails
from shared import get_driver
from result import Ok, Err, Result, is_ok, is_err

# Test using python -m doctest -v download_cb.py
load_dotenv()  # This loads the environment variables from .env
logger = logging.getLogger(__name__)
file_storage_path_base = os.getenv("FILE_STORAGE_PATH", "./output")

base_url = "https://ucnet.universityofcalifornia.edu/resources/employment-policies-contracts/bargaining-units/"  # Collective Bargaining Contracts


def download_pdf(url: str, directory: str, filename: str) -> Result[str, str]:
    """Download PDF files from the web

    Args:
        url: URL of the file to download
        directory: Directory to place the file
        filename: The name of the file to save

    Returns:
       Result: Ok if the file was downloaded, Err if there was an error

    >>> download_pdf('https://ucnet.universityofcalifornia.edu/labor/bargaining-units/cx/docs/cx_2022-2026_00_complete.pdf', './output/docs/collective_bargaining_contracts', 'cx_2022-2026_00_complete.pdf')
    Err('Already have cx_2022-2026_00_complete.pdf')
    """
    response = requests.get(url, allow_redirects=True)

    # Create the folder if it doesn't exist
    os.makedirs(directory, exist_ok=True)

    path = os.path.join(directory, filename)
    # if we already have the file, skip it
    if os.path.exists(path):
        logger.info(f"Already have {filename}")
        return Err(f"Already have {filename}")

    with open(path, "wb") as file:
        file.write(response.content)

    if not os.path.exists(path):
        logger.error(f"Failed to download {filename}")
        return Err(f"Failed to download {filename}")

    return Ok(f"Downloaded {filename}")


class UnionDetail:
    def __init__(self, name: str, code: str, url: str):
        self.name = name
        self.code = code
        self.url = url

    def __repr__(self):
        return f"UnionDetail(name={self.name}, code={self.code}, url={self.url})"


def get_unions(url: str) -> list[UnionDetail]:
    # Get the list of unions from the UCOP website
    # Union links will look like this:
    # <a href="/resources/employment-policies-contracts/bargaining-units/skilled-craft-davis/">Skilled Craft&nbsp;—&nbsp;K3<br></a>
    # pull out name (Skilled Craft), code (K3), and link (/resources/employment-policies-contracts/bargaining-units/skilled-craft-davis/
    driver = get_driver()
    driver.get(url)

    try:
        # Wait for the page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "local"))
        )
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "systemwide"))
        )
    except Exception as e:
        logger.error(f"Error waiting for page to load: {e}")
        return None, None

    soup = BeautifulSoup(driver.page_source, "html.parser")

    union_details = []

    # Finding all the relevant links
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        full_text = ""

        # Check if anchor tag has nested spans
        span_tags = a_tag.find_all("span")
        if span_tags:
            # Assuming the first span tag contains the required text
            full_text = span_tags[0].get_text(strip=True)
        else:
            # Directly get the text inside the anchor tag
            full_text = a_tag.get_text(strip=True)

        if "—" in full_text:
            name, code = full_text.split("—")
            name = name.strip()
            code = code.strip()
            union_detail = UnionDetail(name=name, code=code, url=href)
            union_details.append(union_detail)

    driver.quit()
    return union_details


def get_union_contracts(unions: list[UnionDetail]) -> list[PolicyDetails]:
    # each union url has `/contract/` endpoint which lists all pdfs of contract for that union
    # for each union, get the list of contracts as PolicyDetails objects
    driver = get_driver()

    policy_details_list: list[PolicyDetails] = []

    for union in unions:
        url = union.url
        contract_url = f"{url}/contract/"

        driver.get(contract_url)

        try:
            # Wait for contract detail page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "content-detail__content"))
            )
        except Exception as e:
            logger.error(f"Error waiting for page to load: {e}")
            return None, None

        soup = BeautifulSoup(driver.page_source, "html.parser")
        content_detail = soup.find(id="content-detail__content")

        # find all PDF links within the content-detail__content div
        # links will look like this: <a href="https://ucnet.universityofcalifornia.edu/labor/bargaining-units/ra/docs/ra_00_2022-ta_agreement.pdf">Academic Researchers Tentative Agreement, effective 12-9-2022</a>
        if content_detail:
            # Finding all 'a' tags within this section
            for a_tag in content_detail.find_all("a", href=True):
                href = a_tag["href"]

                # Filtering PDF links
                if href.endswith(".pdf"):
                    # Extracting the title from the href
                    title = href.split("/")[-1].replace(".pdf", "")

                    # Create PolicyDetails instance and append to the list
                    policy_detail = PolicyDetails(
                        title=title,
                        url=href,
                        keywords=[union.code, union.name],
                        subject_areas=["Collective Bargaining"],
                    )
                    policy_details_list.append(policy_detail)

    driver.quit()
    return policy_details_list


def download_cb(update_progress):
    """Download the collective bargaining contracts from UCOP
    Crawls the barganing contracts pages and downloads all the PDFs

    Args:
        update_progress (_type_): A function to update the progress bar
    """
    update_progress("Downloading the collective bargaining contracts...")

    # pull a list of all policies
    home_url = f"{base_url}"

    unions = get_unions(home_url)

    update_progress(f"Found {len(unions)} unions")

    ### For testing purposes, only get the first 3 unions
    policy_details = get_union_contracts(unions[0:3])

    update_progress(f"Found {len(policy_details)} policies")

    # Create a directory to save the PDFs
    directory = os.path.join(
        file_storage_path_base, "./docs/collective_bargaining_contracts"
    )
    os.makedirs(directory, exist_ok=True)

    # save the list of policies with other metadata to a JSON file for later
    policy_details_json_path = os.path.join(directory, "metadata.json")

    # delete the file if it exists
    try:
        os.remove(policy_details_json_path)
    except OSError:
        pass

    with open(policy_details_json_path, "w") as f:
        json.dump([policy.__dict__ for policy in policy_details], f, indent=4)

    # Download the PDFs
    for i, link_info in enumerate(policy_details):
        url = link_info.url
        title = link_info.title
        pdf_filename = f"{link_info.filename}.pdf"

        # update progress every 20 PDFs
        if (i + 1) % 20 == 0:
            update_progress(
                f"Downloading {title} from {url} as {pdf_filename} - {i+1} of {len(policy_details)}"
            )

        download_pdf(url, directory, pdf_filename)

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

    update_progress("Finished UCNET Collective Bargaining download process")


if __name__ == "__main__":
    download_cb(print)
