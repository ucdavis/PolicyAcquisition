from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import requests
import re

def sanitize_filename(filename):
    """Sanitize the filename by removing or replacing invalid characters."""
    return re.sub(r'[\\/*?:"<>|]', '', filename)

def download_pdf(url, filename):
    response = requests.get(url, allow_redirects=True)
    with open(filename, 'wb') as file:
        file.write(response.content)

def get_iframe_src_and_title(driver, url):
    driver.get(url)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'document-viewer'))
        )
    except Exception as e:
        print(f"Error waiting for iframe: {e}")
        return None, None

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    iframe = soup.find(id='document-viewer')
    title_element = soup.find(class_='doc_title')
    title = title_element.get_text(strip=True) if title_element else 'Untitled'
    return (iframe['src'] if iframe else None, title)

def get_links_selenium(driver, url):
    driver.get(url)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'browse-link'))
        )
    except Exception as e:
        print(f"Error waiting for content: {e}")
        return []

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    return [a['href'] for a in soup.select('div.browse-link a')]

# Setup WebDriver using ChromeDriverManager
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)

base_url = 'https://ucdavispolicy.ellucid.com'
home_url = f'{base_url}/manuals/binder/11'

# Get folder links
folder_links = get_links_selenium(driver, home_url)

print(len(folder_links))

# for testing, only use the first 2 links
folder_links = folder_links[:2]

# Iterate over folders and get document links
for folder_link in folder_links:
    document_links = get_links_selenium(driver, f'{base_url}{folder_link}')

    print('Got back documents' + str(len(document_links)))

    # Iterate over documents and download PDFs
    for doc_link in document_links:
        pdf_src, title = get_iframe_src_and_title(driver, f'{base_url}{doc_link}')
        print('found source for PDF: ' + pdf_src + ' with name ' + title)
        if pdf_src:
            pdf_url = f'{base_url}{pdf_src}'
            sanitized_title = sanitize_filename(title)
            filename = f"{sanitized_title}.pdf"
            # Download PDF
            download_pdf(pdf_url, filename)
            print(f'Downloaded {filename}')

# Close the driver
driver.quit()
