import os
from fastapi import APIRouter, UploadFile, File, HTTPException
from .youtube import YoutubeClient

router = APIRouter()

YOUTUBE_HEADERS_PATH = "browser.json"   # store it in root folder


@router.post("/youtube/auth/upload")
async def upload_youtube_headers(file: UploadFile = File(...)):
    content = await file.read()

    try:
        with open(YOUTUBE_HEADERS_PATH, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "YouTube headers uploaded successfully."}


def get_youtube_client():
    if not os.path.exists(YOUTUBE_HEADERS_PATH):
        raise HTTPException(400, "YouTube headers not uploaded")
    return YoutubeClient(YOUTUBE_HEADERS_PATH)


@router.get("/youtube/search")
def yt_search(q: str):
    yt = get_youtube_client()
    return yt.search(q)


@router.post("/youtube/create_playlist")
def yt_create_playlist(title: str, description: str = ""):
    yt = get_youtube_client()
    playlist_id = yt.create_playlist(title, description)
    return {"playlist_id": playlist_id}


@router.post("/youtube/add")
def yt_add(playlist_id: str, video_id: str):
    yt = get_youtube_client()
    return yt.add_to_playlist(playlist_id, [video_id])
