# Use the specific base image
FROM mcr.microsoft.com/devcontainers/python:3.11

# Install OS-level packages

# Update the package list
RUN apt-get update

# Remember to use `-y` to avoid prompts asking for confirmation during the build
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    # add more packages as needed \
    && rm -rf /var/lib/apt/lists/*  # Clean up to keep the image size down