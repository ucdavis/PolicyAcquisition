FROM --platform=linux/amd64 python:3.11-slim

# Install dependencies required for adding a new repository
RUN apt-get update && apt-get install -y wget gnupg2

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

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt

# Copy the current directory contents into the container
COPY . .

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variable
ENV UVICORN_HOST=0.0.0.0
ENV UVICORN_PORT=8000
ENV UVICORN_LOG_LEVEL=info

# Run app.py when the container launches using Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]