# Requires: fastapi, uvicorn, yt-dlp, python-multipart, zipfile, tempfile
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import yt_dlp
import tempfile
import os
import shutil
import zipfile
import json

app = FastAPI()
app.mount("/static", StaticFiles(directory="static", html=True), name="static")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.post("/api/download")
async def download(request: Request):
    data = await request.json()
    links = data.get('links', [])
    fmt = data.get('format', 'mp4')
    tempdir = tempfile.mkdtemp()
    files = []

    ydl_opts = {
        'outtmpl': os.path.join(tempdir, '%(title)s.%(ext)s'),
        'quiet': True,
    }
    if fmt == 'mp3':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        })
    else:
        ydl_opts.update({'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4'})

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for url in links:
            try:
                info = ydl.extract_info(url, download=True)
                files.append(ydl.prepare_filename(info).replace('.webm', '.mp3' if fmt == 'mp3' else '.mp4'))
            except Exception:
                pass

    zip_path = tempfile.mktemp(suffix='.zip')
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file in files:
            if os.path.exists(file):
                zipf.write(file, arcname=os.path.basename(file))

    def iterfile():
        with open(zip_path, mode="rb") as file_like:
            yield from file_like
        shutil.rmtree(tempdir, ignore_errors=True)
        os.remove(zip_path)

    return StreamingResponse(iterfile(), media_type="application/zip", headers={
        "Content-Disposition": f"attachment; filename=downloads.zip"
    })