from selenium import webdriver
from selenium.webdriver.chrome.options import Options

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