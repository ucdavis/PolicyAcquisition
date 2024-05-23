import logging
import os
import uuid
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import APIKeyHeader
import threading
from convert_pdfs import convert_pdfs
from download_academic_affairs import download_academic_affairs
from download_cb import download_cb
from download_ucd_policies import download_ucd

from download_ucop_policies import download_ucop
from repository_sync import reset_file_storage_folder, sync_policies
from vectorize import vectorize

load_dotenv()  # This loads the environment variables from .env

### Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

### Setup API Key Security
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

### In-memory storage for task progress
tasks_progress = {}


def update_task_progress(task_id, progress_update):
    """Append progress update to the task's history."""
    if task_id not in tasks_progress:
        tasks_progress[task_id] = ""
    tasks_progress[task_id] += f"{progress_update}\n"


### Our download methods
def long_running_download_ucop(task_id):
    def update_progress(progress):
        """Local function to update the task progress."""
        update_task_progress(task_id, progress)

    download_ucop(update_progress)
    pass


def long_running_download_ucd(task_id):
    def update_progress(progress):
        """Local function to update the task progress."""
        update_task_progress(task_id, progress)

    download_ucd(update_progress)
    pass


def long_running_download_cb(task_id):
    def update_progress(progress):
        """Local function to update the task progress."""
        update_task_progress(task_id, progress)

    download_cb(update_progress)
    pass


def long_running_download_academic_affairs(task_id):
    def update_progress(progress):
        """Local function to update the task progress."""
        update_task_progress(task_id, progress)

    download_academic_affairs(update_progress)
    pass


def long_running_download_all(task_id):
    def update_progress(progress):
        """Local function to update the task progress."""
        update_task_progress(task_id, progress)

    download_ucop(update_progress)
    download_ucd(update_progress)
    download_cb(update_progress)
    download_academic_affairs(update_progress)
    pass


### Other long running methods
def long_running_convert_pdfs(task_id):
    def update_progress(progress):
        """Local function to update the task progress."""
        update_task_progress(task_id, progress)

    convert_pdfs(update_progress)
    pass


def long_running_sync_content(task_id):
    def update_progress(progress):
        """Local function to update the task progress."""
        update_task_progress(task_id, progress)

    sync_policies(update_progress)
    pass


def long_running_vectorize(task_id):
    def update_progress(progress):
        """Local function to update the task progress."""
        update_task_progress(task_id, progress)

    vectorize(update_progress)
    pass


### Our API Endpoints
@app.post("/api/downloadAcademicAffairs")
async def start_downloadAcademicAffairs():
    # Use threading to avoid blocking the execution
    task_id = str(uuid.uuid4())
    thread = threading.Thread(
        target=long_running_download_academic_affairs, args=(task_id,)
    )
    thread.start()
    return {"message": "Download started successfully", "task_id": task_id}


@app.post("/api/downloadUcop")
async def start_downloadUcop():
    # Use threading to avoid blocking the execution
    task_id = str(uuid.uuid4())
    thread = threading.Thread(target=long_running_download_ucop, args=(task_id,))
    thread.start()
    return {"message": "Download started successfully", "task_id": task_id}


@app.post("/api/downloadUcd")
async def start_downloadUcd():
    # Use threading to avoid blocking the execution
    task_id = str(uuid.uuid4())
    thread = threading.Thread(target=long_running_download_ucd, args=(task_id,))
    thread.start()
    return {"message": "Download started successfully", "task_id": task_id}


@app.post("/api/downloadCb")
async def start_downloadCb():
    # Use threading to avoid blocking the execution
    task_id = str(uuid.uuid4())
    thread = threading.Thread(target=long_running_download_cb, args=(task_id,))
    thread.start()
    return {"message": "Download started successfully", "task_id": task_id}


@app.post("/api/downloadAll")
async def start_downloadAll():
    # Use threading to avoid blocking the execution
    task_id = str(uuid.uuid4())
    thread = threading.Thread(target=long_running_download_all, args=(task_id,))
    thread.start()
    return {"message": "Download started successfully", "task_id": task_id}


@app.post("/api/convertPdfs")
async def start_convertPdfs():
    # Use threading to avoid blocking the execution
    task_id = str(uuid.uuid4())
    thread = threading.Thread(target=long_running_convert_pdfs, args=(task_id,))
    thread.start()
    return {"message": "Conversion started successfully", "task_id": task_id}


@app.post("/api/syncPolicies")
async def start_sync_policies():
    # Use threading to avoid blocking the execution
    task_id = str(uuid.uuid4())
    thread = threading.Thread(target=long_running_sync_content, args=(task_id,))
    thread.start()
    return {"message": "Sync started successfully", "task_id": task_id}


@app.post("/api/vectorize")
async def start_vectorize():
    # Use threading to avoid blocking the execution
    task_id = str(uuid.uuid4())
    thread = threading.Thread(target=long_running_vectorize, args=(task_id,))
    thread.start()
    return {"message": "Vectorization started successfully", "task_id": task_id}


@app.post("/api/clearContent")
async def clear_content():
    # just clear the content folder, no need to thread
    reset_file_storage_folder()

    return {"message": "Content folder cleared successfully"}


### Status Endpoint
# This endpoint will return the history of the given task
# Note this is just stored in-memory and will be lost if the server is restarted
@app.get("/api/task_progress/{task_id}")
async def get_task_progress(task_id: str):
    progress = tasks_progress.get(task_id, "Task not found or completed")
    if progress == "":
        progress = "Task not found or completed"
    return {"task_id": task_id, "progress": progress}


### Health Check & Ancillary Endpoints
@app.get("/")
async def root():
    return {"message": "Welcome to the UCOP Policies Downloader!"}


@app.get("/api/health")
async def health():
    return {"message": "Healthy"}
