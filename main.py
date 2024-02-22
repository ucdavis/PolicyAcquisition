import os
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import APIKeyHeader
import threading



from download_ucop_policies import download_ucop

load_dotenv()  # This loads the environment variables from .env

API_KEY = os.getenv("POLICY_API_KEY")
API_KEY_NAME = "X-API-KEY"

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

async def get_api_key(api_key_header: str = Depends(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )

app = FastAPI(dependencies=[Depends(get_api_key)])

def long_running_download_ucop():
    download_ucop()
    pass

@app.get("/api/downloadUcop")
async def start_downloadUcop():
    # Use threading to avoid blocking the execution
    thread = threading.Thread(target=long_running_download_ucop)
    thread.start()
    return {"message": "Download Ucop started successfully"}

@app.get("/")
async def root():
    return {"message": "Welcome to the UCOP Policies Downloader!"}

@app.get("/api/health")
async def health():
    return {"message": "Healthy"}