from urllib.parse import urljoin
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
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
import json

from policy_details import PolicyDetails

load_dotenv()  # This loads the environment variables from .env

file_storage_path_base = os.getenv("FILE_STORAGE_PATH", "./output")

## UCD Policies are on `https://ucdavispolicy.ellucid.com`
## There are several different binders each with their own set of policies
base_url = "https://ucdavispolicy.ellucid.com"
home_url_minus_binder = f"{base_url}/manuals/binder"

# make a dictionary of the different binders
binders = {
    "11": "ucdppm",
    "13": "ucdppsm",
    "243": "ucdinterim",
    "15": "ucddelegation",
}

# never navigate into these folders
ignore_folders = ["Parent Directory"]
# tag these folders as revision history
# revision_folders = ["PPM Revision History", "PPSM Revision History"]

user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def sanitize_filename(filename):
    """Sanitize the filename by removing or replacing invalid characters."""
    return re.sub(r'[\\/*?:"<>|]', "", filename)


def download_pdf(url, directory, filename):
    headers = {"User-Agent": user_agent}
    response = requests.get(url, headers=headers, allow_redirects=True)

    # Create the folder if it doesn't exist
    os.makedirs(directory, exist_ok=True)

    with open(os.path.join(directory, filename), "wb") as file:
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

    return get_policy_details_from_table(soup)

def get_policy_details_from_table(soup: BeautifulSoup):
    """
    Extracts policy details from a table in the given BeautifulSoup object.

    Args:
        soup (BeautifulSoup): The BeautifulSoup object representing the HTML page.

    Returns:
        List[PolicyDetails]: A list of PolicyDetails objects containing the extracted policy details.
    """
    all_links: List[PolicyDetails] = []

    # main table is div with class="ag-center-cols-container"
    # inside are divs role="row" and we want to iterate over them
    rows = soup.select("div.ag-center-cols-container div[role=row]")

    for row in rows:
        policyRow = PolicyDetails()

        # go through the cells in the row, each are divs with role="gridcell"
        # we want the `col-id` and the text inside the div
        columns = row.select("div[role=gridcell]")

        for column in columns:
            col_id = column["col-id"]
            text = column.text.strip()
            
            if col_id == "approvedOn":
                policyRow.effective_date = text
                policyRow.issuance_date = text
            elif col_id == "keywords":
                policyRow.keywords = [keyword.strip() for keyword in text.split(",")]
            elif col_id == "standardReferences":
                policyRow.subject_areas = [area.strip() for area in text.split(";")]
            elif col_id == "documentClassifications":
                policyRow.classifications = [classification.strip() for classification in text.split(",")]
            elif col_id == "element":
                # this is the actual document link
                # we want to look inside this column and pull out the div.browse-link -> a tag
                a = column.select_one("div.browse-link a")
                policyRow.title = a.text.strip()
                policyRow.url = urljoin(base_url, a["href"])
                policyRow.filename = sanitize_filename(policyRow.title)

        print(policyRow)
        all_links.append(policyRow)

    return all_links

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

    # now we want to add all the columns, so we need to click the column button and then click all the checkboxes
    column_button = driver.find_element(By.CLASS_NAME, "ag-side-button")
    column_button.click()

    WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.CLASS_NAME, "ag-column-tool-panel-column")))

    checkbox_spans = driver.find_elements(By.CLASS_NAME, "ag-column-tool-panel-column")

    # click all the checkboxes
    for cb in checkbox_spans:
        cb.click()

    # wait for the page to update. It's pretty fast to 3 seconds should be enough
    time.sleep(3)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    file_links: List[PolicyDetails] = []

    # first get all links on the homepage of the binder
    all_links: List[PolicyDetails] = get_policy_details_from_table(soup)

    # links will either be a folder or a document
    # folders will start with `/manuals/binder` and documents will start with `/documents`
    # if we find a folder, we need to go into it and get the documents
    for link in all_links:
        # if the folder is in the ignore list, skip it
        if link.title in ignore_folders:
            continue

        if "/manuals/binder" in link.url:
            nested_links = get_links_selenium(driver, link.url)

            # occasionally we can go 3 levels deep
            for nested_link in nested_links:
                if nested_link.title in ignore_folders:
                    continue

                if "/manuals/binder" in nested_link.url:
                    deep_nested_links = get_links_selenium(
                        driver, nested_link.url
                    )

                    for deep_nested_link in deep_nested_links:
                        if deep_nested_link.title in ignore_folders:
                            continue

                        if "/documents" in deep_nested_link.url:
                            file_links.append(deep_nested_link)
                else:
                    file_links.append(nested_link)
        else:
            file_links.append(link)

    return file_links

# downloads files but will not go into folders
def download_all_file_links(driver, directory, doc_links: List[PolicyDetails], update_progress):
    if not isinstance(doc_links, list):
        raise TypeError("doc_links must be a list")

    total_links = len(doc_links)

    # provide 20 status updates during the process
    total_updates = 20

    # Calculate the frequency of updates
    update_frequency = total_links // total_updates
    
    # Iterate over dock_links and download each file
    for i, doc_link in enumerate(doc_links):
        filename = f"{sanitize_filename(doc_link.title)}.pdf"

        if (i +  1) % update_frequency ==  0:
            progress_percentage = round(((i+1) / total_links) *  100,  2)
            update_progress(f"{progress_percentage:.2f}% - Downloading {filename} - {i+1} of {total_links}")

        # if we already have the file, skip it
        if os.path.exists(os.path.join(directory, filename)):
            print(f"Already have {filename}")
            continue

        pdf_src, _ = get_iframe_src_and_title(driver, doc_link.url)

        if pdf_src:
            pdf_url = urljoin(base_url, pdf_src)

            print("found source for PDF: " + pdf_url + " with name " + filename)
            # Download PDF
            download_pdf(pdf_url, directory, filename)
            print(f"Downloaded {filename}")

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
def download_ucd(update_progress):
    """Download all UCD Ellucid policies and save them to the file storage path."""

    driver = get_driver()

    update_progress("Starting UCD download process...")

    for binder in binders:
        update_progress(f"Starting download for {binders[binder]}")

        home_url = f"{home_url_minus_binder}/{binder}"
        file_links = get_nested_links_selenium(driver, home_url)

        print("Got back all links" + str(len(file_links)))
        print(file_links[0])

        update_progress(f"Got back {len(file_links)} links for {binders[binder]}")

        binderName = binders[binder]
        # create a directory to save the pdfs

        directory = os.path.join(file_storage_path_base, './docs/ucd/', binderName)
        
        os.makedirs(directory, exist_ok=True)

        # save the list of policies with other metadata to a JSON file for later
        policy_details_json = os.path.join(directory, 'metadata.json')

        # delete the file if it exists
        try:
            os.remove(policy_details_json)
        except OSError:
            pass

        with open(os.path.join(directory, 'metadata.json'), 'w') as f:
            json.dump([policy.__dict__ for policy in file_links], f, indent=4)

        download_all_file_links(driver, directory, file_links, update_progress)

    # Close the driver
    driver.quit()
