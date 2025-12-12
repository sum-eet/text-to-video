from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import uuid
import os
from app.generator import render_jiggy_video

app = FastAPI()


# Request Model
class GenerateRequest(BaseModel):
    text: str


# In-Memory Job Store (We will replace this with Supabase in Phase 2)
jobs = {}


@app.get("/")
def read_root():
    return {"status": "JIGGYMAX Engine Online"}


@app.post("/generate")
async def generate_video_endpoint(
    request: GenerateRequest, background_tasks: BackgroundTasks
):
    """
    Starts a background video generation job.
    """
    job_id = str(uuid.uuid4())
    jobs[job_id] = "processing"

    # Send to background task
    background_tasks.add_task(run_generation_task, request.text, job_id)

    return {"job_id": job_id, "status": "queued"}


@app.get("/job/{job_id}")
def check_job_status(job_id: str):
    """
    Check if the video is done.
    """
    status = jobs.get(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")

    if status == "done":
        # In Phase 2, this will return the R2 Cloudflare URL
        return {"status": "done", "download_url": f"/download/{job_id}"}

    return {"status": status}


# Helper to run the heavy code
def run_generation_task(text: str, job_id: str):
    try:
        print(f"Starting job {job_id}")
        output_path = render_jiggy_video(text, job_id)
        if output_path:
            print(f"Job {job_id} complete: {output_path}")
            jobs[job_id] = "done"
            # In Phase 2: Upload to R2 here
        else:
            jobs[job_id] = "error"
    except Exception as e:
        print(f"Job {job_id} failed: {e}")
        jobs[job_id] = "error"


# Temporary endpoint to download file (For testing Phase 1 only)
from fastapi.responses import FileResponse


@app.get("/download/{job_id}")
def download_video(job_id: str):
    file_path = f"/tmp/jiggy_videos/{job_id}.mp4"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"error": "File not found"}
