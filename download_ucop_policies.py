import logging
import os
from datetime import datetime
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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

## UCOP Policies are on `https://policy.ucop.edu`
base_url = 'https://policy.ucop.edu'

user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

def download_pdf(url, directory, filename):
    path = os.path.join(directory, filename)
     # if we already have the file, skip it
    if os.path.exists(path):
        logger.info(f"Already have {filename}")
        return
    
    headers = {
        'User-Agent': user_agent
    }
    response = requests.get(url, headers=headers, allow_redirects=True)
    with open(path, 'wb') as file:
        file.write(response.content)

def get_links(driver, url):
    policy_link_info_list: List[PolicyDetails] = []

    driver.get(url)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'accordion'))
        )
    except Exception as e:
        logger.error(f"Error waiting for page to load: {e}")
        return None, None
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Find the element with the id 'accordion'
    accordion = soup.find(id='accordion')

    # Find all 'a' tags within the accordion with class="blue"
    links = accordion.find_all('a', class_='blue')

    for link in links:
        # Get href directly from the link tag but convert to absolute url
        href = urljoin(base_url, link['href'])

        # For the title, find the first (or only) 'span' with class 'icon pdf' within the link
        span = link.find('span', class_='icon pdf')
        if span:  # Check if the span exists
            title = span.text.strip()
        else:
            title = "Title not found"

        # get the parent of the link and find the next 4 sibling divs - subject areas, effective date, issuance date, responsible office
        parent = link.parent

        # Get the next 4 sibling divs
        siblings = parent.find_next_siblings('div')

        # Get the text from each sibling but ignore the <cite> tag
        subject_areas_text = siblings[0].text.replace(siblings[0].find('cite').text, '').strip()
        effective_date = siblings[1].text.replace(siblings[1].find('cite').text, '').strip()
        issuance_date = siblings[2].text.replace(siblings[2].find('cite').text, '').strip()
        responsible_office = siblings[3].text.replace(siblings[3].find('cite').text, '').strip()
        classifications = ["Policy"]

        # subject areas is a comma separated list, so split it into a list
        subject_areas = [area.strip() for area in subject_areas_text.split(',')]

        policy_link_info_list.append(PolicyDetails(title, href, effective_date, issuance_date, responsible_office, subject_areas, [], classifications))

    return policy_link_info_list

#### Main function
#### This will read all of the policies, store their URLs in metadata.json, and then store each in a file
#### Note: This will only add new policies to the folder, it will not overwrite existing or delete missing
def download_ucop(update_progress):
    """Download all UCOP policies and save them to the file storage path."""
    driver = get_driver()

    update_progress("Starting UCOP download process...")

    # pull a list of all policies
    home_url = f'{base_url}/advanced-search.php?action=welcome&op=browse&all=1'

    link_info_list = get_links(driver, home_url)

    # create a directory to save the pdfs
    directory = os.path.join(file_storage_path_base, './docs/ucop')
    os.makedirs(directory, exist_ok=True)

    # save the list of policies with other metadata to a JSON file for later
    policy_details_json = os.path.join(directory, 'metadata.json')

    # delete the file if it exists
    try:
        os.remove(policy_details_json)
    except OSError:
        pass

    with open(os.path.join(directory, 'metadata.json'), 'w') as f:
        json.dump([policy.__dict__ for policy in link_info_list], f, indent=4)

    total_links = len(link_info_list)

    # provide 20 status updates during the process
    total_updates = 20

    # Calculate the frequency of updates
    update_frequency = total_links // total_updates

    # iterate through the list of links and download the pdfs
    for i, link_info in enumerate(link_info_list):
        url = link_info.url
        title = link_info.title
        pdf_filename = f"{link_info.filename}.pdf"

        if update_frequency > 0 and (i + 1) % update_frequency == 0:
            progress_percentage = round(((i+1) / total_links) *  100,  2)
            update_progress(f"{progress_percentage:.2f}% - Downloading {title} from {url} as {pdf_filename} - {i+1} of {total_links}")

        logger.info(f"Downloading {title} from {url} as {pdf_filename}")
        download_pdf(url, directory, pdf_filename)

    # create a JSON file with run details
    with open(os.path.join(directory, 'run_details.json'), 'w') as f:
        completed_date = datetime.now().isoformat()
        json.dump({"total_policies": total_links, "status": "completed", "completed_date": completed_date}, f, indent=4)

    update_progress("Finished UCOP download process")

    # Close the driver
    driver.quit()