FROM --platform=linux/amd64 python:3.11-slim

# Install dependencies required for adding a new repository
RUN apt-get update && apt-get install -y wget gnupg2

# Adding Google Chrome (for selenium) and Tesseract for OCR. Git for using github
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list' && \
    apt-get update && apt-get install -y \
    git \
    google-chrome-stable \
    # Add additional packages here, before the cleanup line
    && rm -rf /var/lib/apt/lists/*  # Clean up to keep the image size down

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set the PYTHONPATH environment variable so we can import modules from the app
ENV PYTHONPATH=/app

# Copy the current directory contents into the container
COPY . .

ENTRYPOINT ["python", "watchdog.py"]