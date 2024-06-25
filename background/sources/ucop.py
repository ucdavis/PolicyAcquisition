import logging
import os
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from typing import List
from urllib.parse import urljoin
import os

from background.models.policy_details import PolicyDetails

load_dotenv()  # This loads the environment variables from .env

logger = logging.getLogger(__name__)

file_storage_path_base = os.getenv("FILE_STORAGE_PATH", "./output")

## UCOP Policies are on `https://policy.ucop.edu`
base_url = "https://policy.ucop.edu"

user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def get_ucop_policies_url():
    return f"{base_url}/advanced-search.php?action=welcome&op=browse&all=1"


def get_ucop_links(driver, url):
    policy_link_info_list: List[PolicyDetails] = []

    driver.get(url)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "accordion"))
        )
    except Exception as e:
        logger.error(f"Error waiting for page to load: {e}")
        return None, None

    soup = BeautifulSoup(driver.page_source, "html.parser")

    # Find the element with the id 'accordion'
    accordion = soup.find(id="accordion")

    # Find all 'a' tags within the accordion with class="blue"
    links = accordion.find_all("a", class_="blue")

    for link in links:
        # Get href directly from the link tag but convert to absolute url
        href = urljoin(base_url, link["href"])

        # For the title, find the first (or only) 'span' with class 'icon pdf' within the link
        span = link.find("span", class_="icon pdf")
        if span:  # Check if the span exists
            title = span.text.strip()
        else:
            title = "Title not found"

        # get the parent of the link and find the next 4 sibling divs - subject areas, effective date, issuance date, responsible office
        parent = link.parent

        # Get the next 4 sibling divs
        siblings = parent.find_next_siblings("div")

        # Get the text from each sibling but ignore the <cite> tag
        subject_areas_text = (
            siblings[0].text.replace(siblings[0].find("cite").text, "").strip()
        )
        effective_date = (
            siblings[1].text.replace(siblings[1].find("cite").text, "").strip()
        )
        issuance_date = (
            siblings[2].text.replace(siblings[2].find("cite").text, "").strip()
        )
        responsible_office = (
            siblings[3].text.replace(siblings[3].find("cite").text, "").strip()
        )
        classifications = ["Policy"]

        # subject areas is a comma separated list, so split it into a list
        subject_areas = [area.strip() for area in subject_areas_text.split(",")]

        policy_link_info_list.append(
            PolicyDetails(
                title,
                href,
                effective_date,
                issuance_date,
                responsible_office,
                subject_areas,
                [],
                classifications,
            )
        )

    return policy_link_info_list
