# 📜 PolicyAcquisition: Your Automated Policy Library Creator

Welcome to **PolicyAcquisition**, a set of Python scripts designed to streamline the process of downloading and converting University policies into text format. Whether you're compiling a database, conducting research, or simply need easy access to policy texts, PolicyAcquisition is your efficient, automated solution.

## What Does PolicyAcquisition Offer?
- **Automated Downloads**: Use `download_ucd_policies.py` and `download_ucop_policies.py` to automatically download policy PDFs from the UC Davis and University of California Office of the President (UCOP) websites.
- **Smart Conversion**: The `convert_pdfs.py` script transforms PDF documents into text, ready for analysis or archiving. It includes OCR capabilities for scanned documents, ensuring that even image-based PDFs are converted accurately.

## Features:
- **Ease of Use**: Designed with simplicity in mind, these scripts require minimal setup and can be initiated with a few commands.
- **Devcontainer Support**: Running these scripts in a devcontainer ensures a consistent and isolated development environment, making dependency management a breeze.
- **Docker Integration**: Leverage the power of Docker to run scripts without worrying about setting up a Python environment on your system – all you need is Docker installed.

## Prerequisites:
1. **Docker**: Ensure Docker is installed and running on your machine. [Download Docker](https://www.docker.com/products/docker-desktop)
2. **Visual Studio Code**: For using devcontainers, Visual Studio Code (VS Code) is recommended. [Download VS Code](https://code.visualstudio.com/Download)
3. **Remote - Containers extension for VS Code**: Install the "Remote - Containers" extension in VS Code to work with devcontainers [Dev Containers Plugin](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers).

## Getting Started:
1. **Clone the Repository**: Clone this repository to your local machine.
2. **Open in VS Code**: Open the cloned repository folder in Visual Studio Code.
3. **Reopen in Container**: With the Remote - Containers extension installed, VS Code will prompt you to "Reopen in Container" – do this to ensure all dependencies are correctly set up.
4. **Running the Scripts**:
    - To download UC Davis policies, run:
    ```
    python download_ucd_policies.py
    ```
    - To download UCOP policies, run:
    ```
    python download_ucop_policies.py
    ```
    - To convert downloaded PDFs to text (with OCR if needed), run:
    ```
    python convert_pdfs.py
    ```

## Contribution:
Your contributions are welcome! Whether it's adding new features, improving documentation, or reporting bugs, please feel free to open an issue or submit a pull request.

---

**Dive into PolicyAcquisition and transform how you interact with university policies today!** 📜🔍