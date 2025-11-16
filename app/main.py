from fastapi import FastAPI
from .auth import router as auth_router
from .spotify_routes import router as spotify_router
from .youtube_routes import router as youtube_router
from fastapi.middleware.cors import CORSMiddleware
from .transfer import router as transfer_router

from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
import os


app = FastAPI(
    title="Spotify → YouTube Playlist Migrator",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "API is running"}

BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # adjust if needed
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")


@app.get("/", response_class=templates.TemplateResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

app.include_router(auth_router)
app.include_router(spotify_router)
app.include_router(youtube_router)
app.include_router(transfer_router)
