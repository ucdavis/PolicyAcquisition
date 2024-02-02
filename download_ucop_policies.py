from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import requests
import re

## UCOP Policies are on `https://policy.ucop.edu`

user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

def sanitize_filename(filename):
    """Sanitize the filename by removing or replacing invalid characters."""
    return re.sub(r'[\\/*?:"<>|]', '', filename)


def download_pdf(url, filename):
    headers = {
        'User-Agent': user_agent
    }
    response = requests.get(url, headers=headers, allow_redirects=True)
    with open(f'./docs/ucop/{filename}', 'wb') as file:
        file.write(response.content)

def get_links(driver, url):
    policy_link_info_list = []

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
        href = link['href']  # Get href directly from the link tag
        # For the title, find the first (or only) 'span' with class 'icon pdf' within the link
        span = link.find('span', class_='icon pdf')
        if span:  # Check if the span exists
            title = span.text.strip()
        else:
            title = "Title not found"

        policy_link_info_list.append((href, title))

    return policy_link_info_list

# Setup WebDriver using ChromeDriverManager
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)

base_url = 'https://policy.ucop.edu'
# pull a list of all policies
home_url = f'{base_url}/advanced-search.php?action=welcome&op=browse&all=1'

link_info_list = get_links(driver, home_url)

# iterate through the list of links and download the pdfs
for link_info in link_info_list:
    href, title = link_info
    print(f"Downloading {title} from {href}")
    download_pdf(f"{base_url}/{href}", f"{sanitize_filename(title)}.pdf")

print(link_info_list)

# Close the driver
driver.quit()
