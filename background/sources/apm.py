import logging
import os
from typing import List
from urllib.parse import urljoin
from dotenv import load_dotenv

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

from background.models.policy_details import PolicyDetails

load_dotenv()  # This loads the environment variables from .env

logger = logging.getLogger(__name__)

## UC Davis Academic Affairs Policies are on `https://academicaffairs.ucdavis.edu/`
## Covers APM (Academic Personnel Manual), plus other policies that we may want to include
base_url = "https://academicaffairs.ucdavis.edu/"

user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


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


def get_apm_url():
    return urljoin(base_url, "apm/apm-toc")
