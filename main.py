from fastapi import FastAPI
import threading

from download_ucop_policies import download_ucop

app = FastAPI()

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