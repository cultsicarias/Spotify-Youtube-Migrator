# app/auth.py
import os
import time
import urllib.parse
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
import requests

load_dotenv()

router = APIRouter()

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")
SPOTIFY_SCOPE = "playlist-read-private playlist-read-collaborative user-read-private"

# In-memory storage for now
user_tokens = {}  # example: {"spotify": {"access_token": "...", "refresh_token":"...", "expires_in":3600, "obtained_at": 169...}}

@router.get("/auth/spotify/login")
def spotify_login():
    params = {
        "response_type": "code",
        "client_id": SPOTIFY_CLIENT_ID,
        "redirect_uri": SPOTIFY_REDIRECT_URI,
        "scope": SPOTIFY_SCOPE,
    }
    url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(params)
    return RedirectResponse(url)

def request_token_with_code(code: str):
    token_url = "https://accounts.spotify.com/api/token"
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": SPOTIFY_REDIRECT_URI,
        "client_id": SPOTIFY_CLIENT_ID,
        "client_secret": SPOTIFY_CLIENT_SECRET
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    resp = requests.post(token_url, data=payload, headers=headers)
    resp.raise_for_status()
    return resp.json()

def request_token_with_refresh_token(refresh_token: str):
    token_url = "https://accounts.spotify.com/api/token"
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": SPOTIFY_CLIENT_ID,
        "client_secret": SPOTIFY_CLIENT_SECRET
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    resp = requests.post(token_url, data=payload, headers=headers)
    resp.raise_for_status()
    return resp.json()

@router.get("/auth/spotify/callback")
def spotify_callback(code: str = None, error: str = None):
    if error:
        raise HTTPException(status_code=400, detail=f"Spotify auth error: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="Missing code in callback")

    token_data = request_token_with_code(code)

    # Add timestamp for expiry management
    token_data["obtained_at"] = int(time.time())

    # store
    user_tokens["spotify"] = token_data

    return {
        "message": "Spotify login successful. Tokens saved in-memory.",
        "tokens": {
            "access_token": token_data.get("access_token"),
            "refresh_token": token_data.get("refresh_token"),
            "expires_in": token_data.get("expires_in")
        }
    }

# Debug endpoint to inspect tokens quickly
@router.get("/debug/tokens")
def debug_tokens():
    if not user_tokens:
        return {"message": "no tokens stored"}
    return user_tokens

# Small helper to refresh and update stored token
def refresh_spotify_token_if_needed():
    """
    If access token expired (or close to expiring), refresh it using refresh_token.
    Returns True if token was refreshed, False otherwise.
    """
    spotify = user_tokens.get("spotify")
    if not spotify:
        raise Exception("No spotify tokens found")

    expires_in = spotify.get("expires_in")
    obtained_at = spotify.get("obtained_at", 0)
    now = int(time.time())

    # refresh if token expired or will expire within 60s
    if (obtained_at + expires_in - 60) <= now:
        refresh_token = spotify.get("refresh_token")
        if not refresh_token:
            raise Exception("No refresh token available to refresh access token")

        new_token_data = request_token_with_refresh_token(refresh_token)
        # Spotify may or may not return a new refresh_token
        if "refresh_token" not in new_token_data:
            new_token_data["refresh_token"] = refresh_token

        new_token_data["obtained_at"] = int(time.time())
        user_tokens["spotify"] = new_token_data
        return True

    return False
