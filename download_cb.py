import logging
import os
from datetime import datetime
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from bs4 import BeautifulSoup
from typing import List
from urllib.parse import urljoin
import requests
import re
import json
import os
from policy_details import PolicyDetails
from shared import get_driver

load_dotenv()  # This loads the environment variables from .env

logger = logging.getLogger(__name__)

file_storage_path_base = os.getenv("FILE_STORAGE_PATH", "./output")

## Collective Bargaining Contracts
base_url = "https://ucnet.universityofcalifornia.edu/labor"

user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def download_pdf(url, directory, filename):
    """ Download PDF files from the web

    Args:
        url (_type_): URL of the file to download
        directory (_type_): Directory to place the file
        filename (_type_): The name of the file to save
    """
    path = os.path.join(directory, filename)
    # if we already have the file, skip it
    if os.path.exists(path):
        logger.info(f"Already have {filename}")
        return
    
    headers = {
        "User-Agent": user_agent
    }
    response = requests.get(url, headers=headers, allow_redirects=True)
    with open(path, "wb") as file:
        file.write(response.content)


def get_pdf_links_from_page(url):
    """
    Get the PDF links on a page

    >>> get_pdf_links_from_page('https://ucnet.universityofcalifornia.edu/labor/bargaining-units/cx/contract.html')
    ['docs/cx_2022-2026_00_complete.pdf']
    """
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    pdf_links = [a['href'] for a in soup.find_all('a') if a['href'].endswith('.pdf')]

    return pdf_links

def crawl_links(driver, start_url):
    visited_links = set()
    pdf_links = []

    def visit_link(url):
        if url in visited_links:
            return
        
        driver.get(url)
        links = driver.find_elements(By.TAG_NAME, 'a')

        for link in links:
            href = link.get_attribute('href')
            if href.endswith('.pdf'):
                pdf_links.append(href)
            elif href not in visited_links:
                visited_links.add(href)
                try:
                    visit_link(href)
                except StaleElementReferenceException:
                    pass
        
        # visit_link(start_url)

        # for a in soup.find_all('a'):
        #     href = a['href']
        #     if href.endswith('.pdf'):
        #         pdf_links.append(href)
        #     else:
        #         new_url = urljoin(url, href)
        #         visited_links.add(new_url)
        #         visit_link(new_url)

    visit_link(start_url)

    return pdf_links


def download_cb(update_progress):
    """ Download the collective bargaining contracts from UCOP

    Args:
        update_progress (_type_): A function to update the progress bar
    """
    driver = get_driver()

    update_progress("Downloading the collective bargaining contracts...")

    # pull a list of all policies
    home_url = f'{base_url}/index.html'

    pdf_links = get_pdf_links_from_page(home_url)
    # pdf_links = crawl_links(driver, home_url)

    # Create a directory to save the PDFs
    directory = os.path.join(file_storage_path_base, './docs/collective_bargaining_contracts')
    os.makedirs(directory, exist_ok=True)

    # Save the list of policies with other metadata to a JSON file
    contract_details_json = os.path.join(directory, 'metadata.json')

    # delete the file if it exists
    try:
        os.remove(contract_details_json)
    except OSError:
        pass

    with open(os.path.join(directory, 'metadata.json'), 'w') as f:
        json.dump(pdf_links, f, indent=4)

    total_links = len(pdf_links)

    # Create a JSON file with run details
    with open(os.path.join(directory, 'run_details.json'), 'w') as f:
        completed_date = datetime.now().isoformat()
        json.dump({"total_contracts": total_links, "status": "completed", "completed_date": completed_date}, f, indent=4)

    update_progress("Finished downloading the collective bargaining contracts")

    driver.quit()

    # driver.get(base_url)
    # try:
    #     WebDriverWait(driver, 10).until(
    #         EC.presence_of_element_located((By.ID, "content"))
    #     )
    # except Exception as e:
    #     logger.error(f"Error waiting for page to load: {e}")
    #     return None, None
    
    # soup = BeautifulSoup(driver.page_source, "html.parser")

    # # Find the element with the id 'content'
    # content = soup.find(id="content")

    # # Find all 'a' tags within the content
    # a_tags = content.find_all("a")

    # # Find all the links to the contracts
    # links = [a["href"] for a in a_tags if "contracts" in a["href"]]

    # # Get the current year
    # current_year = datetime.now().year

    # # Create the directory to store the files
    # directory = os.path.join(file_storage_path_base, "collective_bargaining_contracts", str(current_year))
    # os.makedirs(directory, exist_ok=True)

    # # Download the files
    # for link in links:
    #     # Get the filename
    #     filename = link.split("/")[-1]
    #     update_progress(f"Downloading {filename}")
    #     download_pdf(link, directory, filename)
    # driver.quit()
    # return directory, links


# if __name__ == "__main__":
#     import doctest
#     doctest.testmod()

download_cb(lambda x: print(x))
