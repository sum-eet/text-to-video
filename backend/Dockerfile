# Use Python 3.10 (Stable, compatible with MoviePy)
FROM python:3.10-slim

# 1. Install System Dependencies (FFmpeg is mandatory for MoviePy)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# 2. Set working directory
WORKDIR /code

# 3. Copy Requirements & Install
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# 4. Copy the Font File (Crucial for branding)
COPY ./Anatoleum.ttf /code/Anatoleum.ttf

# 5. Copy the App Code
COPY ./app /code/app

# 6. Create a temp folder for video generation & set permissions
RUN mkdir -p /tmp/jiggy_videos && chmod 777 /tmp/jiggy_videos

# 7. Start the FastAPI Server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]