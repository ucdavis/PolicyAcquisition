# 📜 PolicyAcquisition: Your Automated Policy Library Creator

Welcome to **PolicyAcquisition**, a worker loop designed to streamline the process of downloading and converting University policies into text format. Uses MongoDB to track sources, documents, and run attempts.  The worker loop is designed to be resilient and can be run in a containerized environment.

## What Does PolicyAcquisition Do?
-- **Resilient update loop**: PolicyAcquisition uses a watchdog process that will automatically restart the download process if it fails.
-- **Download Policies**: Check for sources that need to be updated every minute.  Most sources are set to update once a day.
-- **Crawl Sites**: Will crawl sites to find (currently) PDFs that need to be downloaded, including associated metadata.
-- **Download + Vectorize**: Will download PDFs, check if they are new, and then convert them to text, chunk + vectorize them, and store them in Elasticsearch.


# Contributing to PolicyAcquisition
We welcome contributions to PolicyAcquisition! Whether you're interested in adding new features, improving documentation, or reporting bugs, we encourage you to get involved. Here's how you can get started:

## Prerequisites:
1. **Docker**: Ensure Docker is installed and running on your machine. [Download Docker](https://www.docker.com/products/docker-desktop)
2. **Visual Studio Code**: For using devcontainers, Visual Studio Code (VS Code) is recommended. [Download VS Code](https://code.visualstudio.com/Download)
3. **Remote - Containers extension for VS Code**: Install the "Remote - Containers" extension in VS Code to work with devcontainers [Dev Containers Plugin](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers).

## Getting Started:
1. **Clone the Repository**: Clone this repository to your local machine.
2. **Open in VS Code**: Open the cloned repository folder in Visual Studio Code.
3. **Reopen in Container**: With the Remote - Containers extension installed, VS Code will prompt you to "Reopen in Container" – do this to ensure all dependencies are correctly set up.
4. **Environment Variables**: Get the .env file and place it in the root of the project.
5. **Running the Code**: You can run the code by opening a terminal in VS Code and running `python watchdog.py`.  You can also launch the debugger in VS Code to run the code.

## Architectural Notes:
- **Selenium**: Selenium is used to download policies using headless chrome in production and a selenium docker container in development. If you are running the code in a devcontainer, selenium will be automatically set up for you.
- **File Structure**: Uses temporary directories and files, so nothing is permanently stored on the machine.
- **Metadata**: During the web scraping process, metadata for is collected for each policy according to their custom source handlers.

## Deployment:
We are using an Azure Container App to deploy new versions -- currently the process is manual.  When you want to push a new version, you can do so by running the `./deploy.sh` script.  This will build the Docker image, push it to the Azure Container Registry, and then update the Azure Container App to use the new image.

Note: You will need to have the Azure CLI installed and be logged in to the correct account for this to work.  The deployment script uses the git hash as the tag for the Docker image, so you will need to have a clean working directory to run the script.

---

**Dive into PolicyAcquisition and transform how you interact with university policies today!** 📜🔍