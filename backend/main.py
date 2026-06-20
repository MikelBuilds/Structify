from fastapi import FastAPI, UploadFile, File 
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import shutil

app = FastAPI()
UPLOAD_DIR = Path("uploads/originals")
UPLOAD_DIR.mkdir(parents= True, exist_ok=True)

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    file_path = UPLOAD_DIR / file.filename
    with open(file_path,"wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "message" : "File uploaded succesfully",
        "filename" : file.filename
    }

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)