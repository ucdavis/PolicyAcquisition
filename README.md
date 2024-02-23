# 📜 PolicyAcquisition: Your Automated Policy Library Creator

Welcome to **PolicyAcquisition**, a simple API in front of a set of Python scripts designed to streamline the process of downloading and converting University policies into text format. Whether you're compiling a database, conducting research, or simply need easy access to policy texts, PolicyAcquisition is your efficient, automated solution.

## What Does PolicyAcquisition Offer?
- **Simple API**: PolicyAcquisition provides a simple API to download and convert University policies into text format, making it easy to integrate into your existing systems.
- **Automated Downloads**: Use `/api/downloadUcop` and `/api/downloadUcd` to automatically download policy PDFs from the UC Davis and University of California Office of the President (UCOP) websites.
- **Smart Conversion**: The `/api/convertPdfs` endpoint transforms PDF documents into text, ready for analysis or archiving. It includes OCR capabilities for scanned documents, ensuring that even image-based PDFs are converted accurately. This is intended to be used with `/api/syncPolicies`.
-- **Sync Policies to GitHub**: The `/api/syncPolicies` endpoint uses the conversion system to create or copy text versions of all downloads, and then syncs the downloaded policies to a GitHub repository, ensuring that your policy library is always up-to-date and accessible.
-- **Status Checks**: Use the `/api/status/[ID]` endpoint to check the status of the system, ensuring that everything is running smoothly.

## Features:
- **Ease of Use**: Designed with simplicity in mind, these scripts require minimal setup and can be initiated with a few commands.
- **Devcontainer Support**: Running these scripts in a devcontainer ensures a consistent and isolated development environment, making dependency management a breeze.
- **Docker Integration**: Leverage the power of Docker to run scripts without worrying about setting up a Python environment on your system – all you need is Docker installed.

## Production Process:
- **Download Policies**: Download endpoints will be called to download policies to Azure storage on a regular basis. Note that the download process will skip already downloaded policies, ensuring that only new policies are downloaded.
- **Sync Policies**: The sync endpoint will be called less often, to sync the downloaded policies to a GitHub repository, ensuring that the policy library is always up-to-date and accessible.
- **Reset Policies**: (TODO) The reset endpoint will be called to delete all policies from the Azure storage, allowing for a fresh start.

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
5. **Running the Code**:
    - **Launch API**: Simply run the following command to start the API:
    ```
    uvicorn main:app
    ```
    Note: The API will be available at [http://127.0.0.1:8000](http://127.0.0.1:8000) and you'll need to restart the API after making changes to the code.

## Architectural Notes:
- **Selenium**: Selenium is used to download policies using headless chrome in production and a selenium docker container in development. If you are running the code in a devcontainer, selenium will be automatically set up for you.
- **File Structure**: Downloaded files are written to the `FILE_STORAGE_PATH` directory, `./docs/` for PDF documents, `./text/` for text documents. Inside each directory, there are subdirectories for policy groups (e.g. `./docs/ucop/` and `./docs/ucd/ucdppsm`).
- **Metadata**: During the web scraping process, metadata for is collected and stored in a `metadata.json` file in each subdirectory. Additionally, `run_details.json` is created to store details about the download run -- the presence of this file indicates that the download process was successful.
- **GitHub Sync**: The GitHub sync process creates a temporary directory to store the text versions of the downloaded policies, and then uses `git` to commit and push the changes to the Policy GitHub repository. This will sync all changes, including new policies, updated policies, and deleted policies.

## Deployment:
We are using an Azure Container App to deploy new versions -- currently the process is manual.  When you want to push a new version, you can do so by running the `./deploy.sh` script.  This will build the Docker image, push it to the Azure Container Registry, and then update the Azure Container App to use the new image.

Note: You will need to have the Azure CLI installed and be logged in to the correct account for this to work.  The deployment script uses the git hash as the tag for the Docker image, so you will need to have a clean working directory to run the script.

---

**Dive into PolicyAcquisition and transform how you interact with university policies today!** 📜🔍