FROM mcr.microsoft.com/azure-functions/python:4-python3.11

ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true
    
# Set environment variable for display port
ENV DISPLAY=:99

# Adding Google Chrome (for selenium) and Tesseract for OCR 
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list' && \
    apt-get update && apt-get install -y \
    google-chrome-stable \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    # Add additional packages here, before the cleanup line
    && rm -rf /var/lib/apt/lists/*  # Clean up to keep the image size down

# Install Python dependencies
COPY requirements.txt /
RUN pip install -r /requirements.txt

COPY . /home/site/wwwroot