from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import requests

service = Service(ChromeDriverManager().install())
options = webdriver.ChromeOptions()

download_dir = "/Users/postit/Documents/projects/ucdpolicies"

user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

prefs = {"plugins.plugins_list": [{"enabled": False, "name": "Chrome PDF Viewer"}]}

# try to not use the built-in chrome pdf viewer
options.add_experimental_option('prefs', prefs)

driver = webdriver.Chrome(service=service, options=options)

url = 'https://ucdavispolicy.ellucid.com/view/revision/3188'
filename = 'test.pdf'

def download_pdf(url, filename):
    headers = {
        'User-Agent': user_agent
    }
    response = requests.get(url, headers=headers, allow_redirects=True)
    with open(f'./docs/{filename}', 'wb') as file:
        file.write(response.content)

def goto_pdf(driver, url):
    # go to the url, it will return a 307 redirect to the pdf
    driver.get(url)
    print('got url')
    print('Redirected URL:', driver.current_url)
    
    download_pdf(driver.current_url, filename)

def get_redirect_url(url):
    response = requests.get(url, allow_redirects=False)
    if response.status_code == 307:
        return response.headers['Location']
    else:
        return None

redirect_url = get_redirect_url(url)
print('Redirect URL:', redirect_url)

download_pdf(redirect_url, filename)

# Close the driver
driver.quit()
