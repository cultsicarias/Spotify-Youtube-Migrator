import os
from ytmusicapi import YTMusic

class YoutubeClient:
    def __init__(self, headers_path: str):
        if not os.path.exists(headers_path):
            raise FileNotFoundError("YouTube headers file not found")
        self.yt = YTMusic(headers_path)

    def create_playlist(self, title: str, description: str = ""):
        return self.yt.create_playlist(title, description)

    def search(self, query: str):
        return self.yt.search(query, filter="songs")

    def add_to_playlist(self, playlist_id: str, video_ids: list[str]):
        return self.yt.add_playlist_items(playlist_id, video_ids)
