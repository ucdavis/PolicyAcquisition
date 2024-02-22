import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
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
from policy_details import PolicyDetails

## UCOP Policies are on `https://policy.ucop.edu`
base_url = 'https://policy.ucop.edu'

user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

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
        classifications = ["Policy"]

        # subject areas is a comma separated list, so split it into a list
        subject_areas = [area.strip() for area in subject_areas_text.split(',')]

        policy_link_info_list.append(PolicyDetails(title, href, effective_date, issuance_date, responsible_office, subject_areas, [], classifications))

    return policy_link_info_list

def get_driver():
    # Try to get the chrome driver, and if not found, use our remove selenium server
    try:
        # Use the ChromeDriverManager to install the latest version of ChromeDriver
        # uncomment if you are running locally and want to see the browser, then modify webdriver.Chrome to use the service
        # service = Service(ChromeDriverManager().install())
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except:
        print("Using remote driver")
        # Set up Selenium options
        options = Options()
        options.add_argument('--headless')  # run headless Chrome
        options.add_argument('--disable-gpu')  # applicable to windows os only
        options.add_argument('--no-sandbox')  # Bypass OS security model
        options.add_argument('--disable-dev-shm-usage')  # overcome limited resource problems

        # Set up the Remote service URL pointing to where the Selenium Server is running
        remote_url = "http://selenium:4444/wd/hub"

        # Create a new instance of Chrome
        driver = webdriver.Remote(
            command_executor=remote_url,
            options=options
        )
        return driver

#### Main function
#### This will read all of the policies, store their URLs in metadata.json, and then store each in a file
#### Note: This will only add new policies to the folder, it will not overwrite existing or delete missing
def download_ucop():
    driver = get_driver()

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

    # Close the driver
    driver.quit()