# app/spotify_routes.py
from fastapi import APIRouter, HTTPException
from .auth import user_tokens, refresh_spotify_token_if_needed
from .spotify import SpotifyClient
import requests

router = APIRouter()

def get_spotify_client():
    # ensure tokens exist
    if "spotify" not in user_tokens:
        raise HTTPException(status_code=401, detail="User not authenticated. Please login at /auth/spotify/login")

    # try to refresh if needed (this mutates user_tokens)
    try:
        refresh_spotify_token_if_needed()
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Failed to refresh token: {str(e)}")

    access_token = user_tokens["spotify"].get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="No access token available")

    return SpotifyClient(access_token)

@router.get("/spotify/me")
def spotify_me():
    client = get_spotify_client()
    data = client.get_user_profile()
    # if Spotify responded with 401, bubble it up
    if isinstance(data, dict) and data.get("error") and data["error"].get("status") == 401:
        raise HTTPException(status_code=401, detail="Spotify returned 401. Token may be invalid.")
    return data

@router.get("/spotify/playlists")
def spotify_playlists():
    client = get_spotify_client()
    return client.get_user_playlists()

@router.get("/spotify/playlist/{playlist_id}/tracks")
def spotify_playlist_tracks(playlist_id: str):
    client = get_spotify_client()
    return client.get_playlist_tracks(playlist_id)
