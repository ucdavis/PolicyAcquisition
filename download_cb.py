import logging
import os
from datetime import datetime
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException
from bs4 import BeautifulSoup
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

base_url = "https://ucnet.universityofcalifornia.edu/labor/bargaining-units"  # Collective Bargaining Contracts


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


def crawl_links(start_url: str, depth=3) -> set[str]:
    """Crawl a website and return all the links
        Crawling is limited to our `base_url`

    Args:
        start_url: The URL to start crawling from
        depth: The depth of links to crawl

    Returns:
        set: A set of all the links found

    >>> result = crawl_links('https://ucnet.universityofcalifornia.edu/labor/bargaining-units/cx/contract.html', 0)
    Using remote driver
    >>> len(result) > 0
    True
    """
    driver = get_driver()
    visited_links = set()
    links_to_visit = [(start_url, 0)]

    while links_to_visit:
        url, current_depth = links_to_visit.pop(0)
        if url in visited_links or current_depth > depth:
            continue

        # only visit links on our base_url
        if not url.startswith(base_url):
            continue

        visited_links.add(url)

        # if we are looking at a PDF, skip it after adding it to the visited links
        if url.endswith(".pdf"):
            continue

        # Visit the page and get all the links
        try:
            driver.get(url)
            links = driver.find_elements(By.TAG_NAME, "a")

            for link in links:
                href = link.get_attribute("href")
                if href and href not in visited_links:
                    links_to_visit.append((href, current_depth + 1))

        except StaleElementReferenceException:
            pass

    driver.quit()

    return visited_links


def download_cb(update_progress):
    """Download the collective bargaining contracts from UCOP
        Crawls the barganing contracts page and downloads all the PDFs
        Future: perhaps save non-PDFs like FAQ and other pages as HTML/text?
                : map 2-character codes to full names

    Args:
        update_progress (_type_): A function to update the progress bar
    """
    update_progress("Downloading the collective bargaining contracts...")

    # pull a list of all policies
    home_url = f"{base_url}/index.html"

    all_links = crawl_links(home_url, 3)

    # get just the links that are PDFs
    pdf_links = [link for link in all_links if link.endswith(".pdf")]

    # transform policy links to a list of PolicyDetails
    # we really just know url and we'll pull title from filename.  would be nice to get more metadata later. maybe via AI?
    policy_details = [
        PolicyDetails(title=os.path.splitext(os.path.basename(link))[0], url=link)
        for link in pdf_links
    ]

    # Create a directory to save the PDFs
    directory = os.path.join(
        file_storage_path_base, "./docs/collective_bargaining_contracts"
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

# if __name__ == "__main__":
#     import doctest
#     doctest.testmod()

download_cb(lambda x: print(x))
