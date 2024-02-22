import os
import uuid
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import APIKeyHeader
import threading

from download_ucop_policies import download_ucop

load_dotenv()  # This loads the environment variables from .env

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

### Our API Endpoints
@app.post("/api/downloadUcop")
async def start_downloadUcop():
    # Use threading to avoid blocking the execution
    task_id = str(uuid.uuid4())
    thread = threading.Thread(target=long_running_download_ucop, args=(task_id,))
    thread.start()
    return {"message": "Download started successfully", "task_id": task_id}

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