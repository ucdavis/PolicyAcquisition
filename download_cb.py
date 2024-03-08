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
from shared import get_driver
from result import Ok, Err, Result, is_ok, is_err

# Test using python -m doctest -v download_cb.py
load_dotenv()  # This loads the environment variables from .env
logger = logging.getLogger(__name__)
file_storage_path_base = os.getenv("FILE_STORAGE_PATH", "./output")
user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
base_url = "https://ucnet.universityofcalifornia.edu/labor" # Collective Bargaining Contracts

def download_pdf(url: str, directory: str, filename: str) -> Result[str, str]:
    """ Download PDF files from the web

    Args:
        url: URL of the file to download
        directory: Directory to place the file
        filename: The name of the file to save

    Returns:
       Result: Ok if the file was downloaded, Err if there was an error

    >>> download_pdf('https://ucnet.universityofcalifornia.edu/labor/bargaining-units/cx/docs/cx_2022-2026_00_complete.pdf', './output/docs/collective_bargaining_contracts', 'cx_2022-2026_00_complete.pdf')
    Err('Already have cx_2022-2026_00_complete.pdf')
    """
    headers = { "User-Agent": user_agent}
    response = requests.get(url, headers=headers, allow_redirects=True)

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

def get_pdf_links_from_page(url: str) -> list[str]:
    """Get the PDF links on a page

    >>> get_pdf_links_from_page('https://ucnet.universityofcalifornia.edu/labor/bargaining-units/cx/contract.html')
    ['docs/cx_2022-2026_00_complete.pdf']
    """
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    pdf_links = [a['href'] for a in soup.find_all('a') if a['href'].endswith('.pdf')]

    return pdf_links

def crawl_links(start_url: str, depth=3) -> set[str]:
    """Crawl a website and return all the links
    
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

        visited_links.add(url)

        try:
            driver.get(url)
            links = driver.find_elements(By.TAG_NAME, 'a')

            for link in links:
                href = link.get_attribute('href')
                if href and href not in visited_links:
                    links_to_visit.append((href, current_depth + 1))

        except StaleElementReferenceException:
            pass

    driver.quit()

    return visited_links

def download_cb(update_progress):
    """ Download the collective bargaining contracts from UCOP

    Args:
        update_progress (_type_): A function to update the progress bar
    """
    # driver = get_driver()

    update_progress("Downloading the collective bargaining contracts...")

    # pull a list of all policies
    home_url = f'{base_url}/index.html'

    links_to_visit = crawl_links(home_url, 2)
    pdf_links = set()

    # Get the PDF links from each page
    for link in links_to_visit:
        pdf_links.append(get_pdf_links_from_page(link))

    # Create a directory to save the PDFs
    directory = os.path.join(file_storage_path_base, './docs/collective_bargaining_contracts')
    os.makedirs(directory, exist_ok=True)

    # Save the list of policies with other metadata to a JSON file
    contract_details_json = os.path.join(directory, 'metadata.json')

    with open(os.path.join(directory, 'metadata.json'), 'w') as f:
        json.dump(pdf_links, f, indent=4)

    for link in pdf_links:
        download_pdf(link, directory, os.path.basename(link))

    total_links = len(pdf_links)

    # Create a JSON file with run details
    with open(os.path.join(directory, 'run_details.json'), 'w') as f:
        completed_date = datetime.now().isoformat()
        json.dump({"total_contracts": total_links, "status": "completed", "completed_date": completed_date}, f, indent=4)

    update_progress("Finished downloading the collective bargaining contracts")

# if __name__ == "__main__":
#     import doctest
#     doctest.testmod()

download_cb(lambda x: print(x))
