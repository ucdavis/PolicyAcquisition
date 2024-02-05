from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from typing import List
import requests
import re
import os
import time

## UCD Policies are on `https://ucdavispolicy.ellucid.com`
## There are several different binders each with their own set of policies

# make a dictionary of the different binders
binders = {
    "11": "ucdppm",
    "13": "ucdppsm",
    "243": "ucdinterim",
    "15": "ucddelegation",
}

# list of folder to ignore
ignore_folders = ["Parent Directory", "PPM Revision History", "PPSM Revision History"]

user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def sanitize_filename(filename):
    """Sanitize the filename by removing or replacing invalid characters."""
    return re.sub(r'[\\/*?:"<>|]', "", filename)


def download_pdf(url, folderName, filename):
    headers = {"User-Agent": user_agent}
    response = requests.get(url, headers=headers, allow_redirects=True)

    # Create the folder if it doesn't exist
    folder_path = f"./docs/{folderName}"
    os.makedirs(folder_path, exist_ok=True)

    with open(os.path.join(folder_path, filename), "wb") as file:
        file.write(response.content)


def get_iframe_src_and_title(driver, url):
    driver.get(url)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "document-viewer"))
        )
    except Exception as e:
        print(f"Error waiting for iframe: {e}")
        return None, None

    soup = BeautifulSoup(driver.page_source, "html.parser")
    iframe = soup.find(id="document-viewer")
    title_element = soup.find(class_="doc_title")
    title = title_element.get_text(strip=True) if title_element else "Untitled"
    return (iframe["src"] if iframe else None, title)


# simple returns all the folder or file links on a page
def get_links_selenium(driver, url):
    driver.get(url)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "browse-link"))
        )
    except Exception as e:
        print(f"Error waiting for content: {e}")
        return []

    soup = BeautifulSoup(driver.page_source, "html.parser")
    return [
        BrowseLink(a["href"], a.text.strip()) for a in soup.select("div.browse-link a")
    ]


# class BrowseLink w/ href and title
class BrowseLink:
    def __init__(self, href, title):
        self.href = href
        self.title = title


# returns file links and can go into folders
# file links include href and title
def get_nested_links_selenium(driver, url):
    driver.get(url)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "browse-link"))
        )
    except Exception as e:
        print(f"Error waiting for content: {e}")
        return []

    # now change the select.page-size element to 100
    select = driver.find_element(By.CLASS_NAME, "page-size")
    select.click()
    select.send_keys("100")

    # wait for the page to update. It's pretty fast to 3 seconds should be enough
    time.sleep(3)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    file_links: List[BrowseLink] = []
    # tuple of href and title
    all_links = [
        BrowseLink(a["href"], a.text.strip())
        for a in soup.select("div.browse-link a")
        if a.text.strip() not in ignore_folders
    ]

    # links will either be a folder or a document
    # folders will start with `/manuals/binder` and documents will start with `/documents`
    # if we find a folder, we need to go into it and get the documents
    for link in all_links:
        if link.href.startswith("/manuals/binder"):
            nested_links = get_links_selenium(driver, f"{base_url}{link.href}")

            # occasionally we can go 3 levels deep
            for nested_link in nested_links:
                if nested_link.href.startswith("/manuals/binder"):
                    deep_nested_links = get_links_selenium(
                        driver, f"{base_url}{nested_link.href}"
                    )

                    for deep_nested_link in deep_nested_links:
                        if deep_nested_link.href.startswith("/documents"):
                            file_links.append(deep_nested_link)
                else:
                    file_links.append(nested_link)
        else:
            file_links.append(link)

    return file_links


# download all the links in a folder. can only go one level deep
def download_all_links(driver, binderName, folder_links):
    # Iterate over folders and get document links
    for folder_link in folder_links:
        document_links = get_links_selenium(driver, f"{base_url}{folder_link}")

        print("Got back documents" + str(len(document_links)))

        # Iterate over documents and download PDFs
        for doc_link in document_links:
            pdf_src, title = get_iframe_src_and_title(driver, f"{base_url}{doc_link}")
            if pdf_src:
                pdf_url = f"{base_url}{pdf_src}"
                sanitized_title = sanitize_filename(title)
                filename = f"{sanitized_title}.pdf"

                # if we already have the file, skip it
                if os.path.exists(f"./docs/{binderName}/{filename}"):
                    print(f"Already have {filename}")
                    continue

                print("found source for PDF: " + pdf_url + " with name " + filename)
                # Download PDF
                download_pdf(pdf_url, binderName, filename)
                print(f"Downloaded {filename}")


# downloads files but will not go into folders
def download_all_file_links(driver, binderName, doc_links: List[BrowseLink]):
    if not isinstance(doc_links, list):
        raise TypeError("doc_links must be a list")

    # Iterate over folders and get document links
    for doc_link in doc_links:
        filename = f"{sanitize_filename(doc_link.title)}.pdf"

        # if we already have the file, skip it
        if os.path.exists(f"./docs/{binderName}/{filename}"):
            print(f"Already have {filename}")
            continue

        pdf_src, _ = get_iframe_src_and_title(driver, f"{base_url}{doc_link.href}")
        if pdf_src:
            pdf_url = f"{base_url}{pdf_src}"

            print("found source for PDF: " + pdf_url + " with name " + filename)
            # Download PDF
            download_pdf(pdf_url, binderName, filename)
            print(f"Downloaded {filename}")


# Setup WebDriver using ChromeDriverManager
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)

base_url = "https://ucdavispolicy.ellucid.com"
home_url_minus_binder = f"{base_url}/manuals/binder"

# go through each binder in dictionary and download all the PDFs
# for binder in binders:
#     home_url = f"{home_url_minus_binder}/{binder}"
#     folder_links = get_links_selenium(driver, home_url)
#     download_all_links(driver, binders[binder], folder_links)

for binder in binders:
    home_url = f"{home_url_minus_binder}/{binder}"
    file_links = get_nested_links_selenium(driver, home_url)
    download_all_file_links(driver, binders[binder], file_links)

# Close the driver
driver.quit()
