import requests

class SpotifyClient:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.api_base = "https://api.spotify.com/v1"

    def get_headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}"
        }

    def get_user_profile(self):
        url = f"{self.api_base}/me"
        return requests.get(url, headers=self.get_headers()).json()

    def get_user_playlists(self):
        url = f"{self.api_base}/me/playlists?limit=50"
        return requests.get(url, headers=self.get_headers()).json()

    def get_playlist_tracks(self, playlist_id: str):
        url = f"{self.api_base}/playlists/{playlist_id}/tracks?limit=100"
        return requests.get(url, headers=self.get_headers()).json()
