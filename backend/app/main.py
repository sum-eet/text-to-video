from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uuid
import os
from app.generator import render_jiggy_video

app = FastAPI()


# UPDATE: Request model now accepts settings
class GenerateRequest(BaseModel):
    text: str
    font: str = "Arial"  # Default if not provided
    use_voice: bool = True  # Default ON


# In-Memory Job Store (Phase 1 Only)
jobs = {}


@app.get("/")
def read_root():
    return {"status": "JIGGYMAX Engine Online v3.0"}


@app.post("/generate")
async def generate_video_endpoint(
    request: GenerateRequest, background_tasks: BackgroundTasks
):
    job_id = str(uuid.uuid4())
    jobs[job_id] = "processing"

    # Pass all new parameters to the background task
    background_tasks.add_task(
        run_generation_task, request.text, request.font, request.use_voice, job_id
    )

    return {"job_id": job_id, "status": "queued"}


@app.get("/job/{job_id}")
def check_job_status(job_id: str):
    status = jobs.get(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")

    if status == "done":
        return {"status": "done", "download_url": f"/download/{job_id}"}

    return {"status": status}


def run_generation_task(text: str, font: str, use_voice: bool, job_id: str):
    try:
        print(f"Starting job {job_id} | Font: {font} | Voice: {use_voice}")
        output_path = render_jiggy_video(text, font, use_voice, job_id)

        if output_path:
            print(f"Job {job_id} complete")
            jobs[job_id] = "done"
        else:
            jobs[job_id] = "error"
    except Exception as e:
        print(f"Job {job_id} failed: {e}")
        jobs[job_id] = "error"


@app.get("/download/{job_id}")
def download_video(job_id: str):
    file_path = f"/tmp/jiggy_videos/{job_id}.mp4"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"error": "File not found"}
