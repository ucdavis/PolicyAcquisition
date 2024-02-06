import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
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

## UCOP Policies are on `https://policy.ucop.edu`
base_url = 'https://policy.ucop.edu'

class PolicyDetails:
    def __init__(self, title, url, effective_date=None, issuance_date=None, responsible_office=None, subject_areas=[]):
        self.title = title
        self.filename = sanitize_filename(title)
        self.effective_date = effective_date
        self.issuance_date = issuance_date
        self.url = url
        self.responsible_office = responsible_office
        self.subject_areas = subject_areas

    def __str__(self):
        return f"{self.title} - {self.url} - {self.effective_date} - {self.issuance_date} - {self.responsible_office} - {self.subject_areas}"

user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

def sanitize_filename(filename):
    """Sanitize the filename by removing or replacing invalid characters."""
    return re.sub(r'[\\/*?:"<>|]', '', filename)


def download_pdf(url, filename):
     # if we already have the file, skip it
    if os.path.exists(f"./docs/ucop/{filename}"):
        print(f"Already have {filename}")
        return
    
    headers = {
        'User-Agent': user_agent
    }
    response = requests.get(url, headers=headers, allow_redirects=True)
    with open(f'./docs/ucop/{filename}', 'wb') as file:
        file.write(response.content)

def get_links(driver, url):
    policy_link_info_list: List[PolicyDetails] = []

    driver.get(url)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'accordion'))
        )
    except Exception as e:
        print(f"Error waiting for page to load: {e}")
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

        # subject areas is a comma separated list, so split it into a list
        subject_areas = subject_areas_text.split(',')

        policy_link_info_list.append(PolicyDetails(title, href, effective_date, issuance_date, responsible_office, subject_areas))

    return policy_link_info_list

# Setup WebDriver using ChromeDriverManager
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)

# pull a list of all policies
home_url = f'{base_url}/advanced-search.php?action=welcome&op=browse&all=1'

link_info_list = get_links(driver, home_url)

# create a directory to save the pdfs
directory = './docs/ucop'
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

# iterate through the list of links and download the pdfs
for link_info in link_info_list:
    url = link_info.url
    title = link_info.title
    pdf_filename = f"{link_info.filename}.pdf"
    print(f"Downloading {title} from {url} as {pdf_filename}")
    download_pdf(url, pdf_filename)

# print(link_info_list)

# Close the driver
driver.quit()
