# app/transfer.py
import asyncio
import math
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from fastapi import APIRouter, HTTPException
from typing import List

from .spotify_routes import get_spotify_client
from .youtube_routes import get_youtube_client

router = APIRouter()

# Tunable
MAX_WORKERS = 8            # number of threads for parallel searches
BATCH_ADD_SIZE = 20        # how many videoIds to add in one API call
CONFIDENCE_THRESHOLD = 0.65  # above this is "good" match


def normalize_text(s: str) -> str:
    return ''.join(c.lower() for c in s if c.isalnum() or c.isspace()).strip()


def title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()


def artist_score(spotify_artists: List[str], yt_title_or_artist: str) -> float:
    # checks if any artist substring appears in YouTube result string
    yt_norm = normalize_text(yt_title_or_artist)
    for artist in spotify_artists:
        if artist and normalize_text(artist) in yt_norm:
            return 1.0
    # partial token overlap fallback
    spotify_tokens = set(" ".join(spotify_artists).lower().split())
    yt_tokens = set(yt_norm.split())
    if not spotify_tokens:
        return 0.0
    overlap = spotify_tokens.intersection(yt_tokens)
    return len(overlap) / max(1, len(spotify_tokens))


def parse_yt_duration(duration_str: str) -> int:
    # "3:45" -> seconds 225 ; "1:02:30" -> seconds
    try:
        parts = [int(p) for p in duration_str.split(":")]
        if len(parts) == 3:
            h, m, s = parts
        elif len(parts) == 2:
            h = 0
            m, s = parts
        elif len(parts) == 1:
            h = 0
            m = 0
            s = parts[0]
        return h * 3600 + m * 60 + s
    except Exception:
        return 0


def duration_score(spotify_ms: int, yt_duration_str: str) -> float:
    if not spotify_ms:
        return 0.0
    spotify_sec = spotify_ms // 1000
    yt_sec = parse_yt_duration(yt_duration_str)
    if yt_sec == 0:
        return 0.0
    diff = abs(spotify_sec - yt_sec)
    # score is 1.0 for exact, fall off with diff
    score = max(0.0, 1.0 - (diff / max(30, spotify_sec)))  # forgiving for long songs
    return score


def compute_score(spotify_track, yt_result) -> float:
    # spotify_track is Spotify track object; yt_result from ytmusicapi search item
    title_sim = title_similarity(spotify_track["name"], yt_result.get("title", ""))
    spotify_artists = [a["name"] for a in spotify_track.get("artists", [])]
    artist_sc = artist_score(spotify_artists, " ".join(spotify_artists) + " " + yt_result.get("artists", "") if isinstance(yt_result.get("artists", ""), str) else " ".join(spotify_artists))
    yt_duration = yt_result.get("duration", "") or ""
    dur_sc = duration_score(spotify_track.get("duration_ms", 0), yt_duration)

    # weights: title (0.5), artist (0.3), duration (0.2)
    return 0.5 * title_sim + 0.3 * artist_sc + 0.2 * dur_sc


async def search_youtube_for_track(executor, youtube_client, spotify_track):
    # Build query
    artist = spotify_track["artists"][0]["name"] if spotify_track.get("artists") else ""
    query = f"{spotify_track['name']} {artist}"
    # ytmusicapi is sync; run in threadpool
    results = await asyncio.to_thread(youtube_client.search, query)
    # Ensure results is a list and items contain videoId,title,duration
    return results or []


@router.post("/transfer")
async def transfer_playlist(spotify_playlist_id: str):
    spotify = get_spotify_client()
    youtube = get_youtube_client()

    # Fetch ALL spotify tracks (our spotify client returns {"items": [...]})
    spotify_tracks_resp = spotify.get_playlist_tracks(spotify_playlist_id)
    items = spotify_tracks_resp.get("items", [])
    if not items:
        raise HTTPException(status_code=404, detail="No tracks found in this playlist")

    # Flatten list of track objects
    tracks = []
    for it in items:
        track = it.get("track")
        if track:
            tracks.append(track)

    # Create new YouTube playlist
    yt_playlist_name = f"Migrated: {spotify_playlist_id}"
    yt_playlist_id = await asyncio.to_thread(youtube.create_playlist, yt_playlist_name, "Migrated from Spotify")

    report = {
        "created_playlist_id": yt_playlist_id,
        "total_spotify_tracks": len(tracks),
        "matches": [],
        "unmatched": []
    }

    loop = asyncio.get_running_loop()
    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

    # Run searches in parallel
    search_tasks = [search_youtube_for_track(executor, youtube, t) for t in tracks]
    all_search_results = await asyncio.gather(*search_tasks)

    # For each track, compute score for top N candidates and pick best
    to_add_video_ids = []
    for idx, spotify_track in enumerate(tracks):
        results = all_search_results[idx]
        best = None
        best_score = -1.0
        # consider top 6 results
        for r in results[:6]:
            # ensure r has 'videoId' and 'title' and maybe 'duration'
            score = compute_score(spotify_track, r)
            if score > best_score:
                best_score = score
                best = r

        if best and best.get("videoId"):
            to_add_video_ids.append(best["videoId"])
            confidence = "high" if best_score >= CONFIDENCE_THRESHOLD else "low"
            report["matches"].append({
                "spotify_track": spotify_track["name"],
                "artist": spotify_track["artists"][0]["name"] if spotify_track.get("artists") else "",
                "video_id": best["videoId"],
                "confidence": confidence,
                "score": round(best_score, 3),
                "yt_title": best.get("title"),
                "yt_duration": best.get("duration")
            })
        else:
            report["unmatched"].append({
                "spotify_track": spotify_track["name"],
                "artist": spotify_track["artists"][0]["name"] if spotify_track.get("artists") else ""
            })

    # Batch-add video IDs to playlist to reduce API calls
    for i in range(0, len(to_add_video_ids), BATCH_ADD_SIZE):
        chunk = to_add_video_ids[i: i + BATCH_ADD_SIZE]
        # ytmusicapi add_playlist_items is sync -> wrap in thread
        await asyncio.to_thread(youtube.add_to_playlist, yt_playlist_id, chunk)

    return report
