import spotipy
from spotipy.oauth2 import SpotifyOAuth
from yt_dlp import YoutubeDL
import os
SPOTIFY_CLIENT_ID = 'bbef9944f39449c2b689b2db4a0a0d1c'
SPOTIFY_CLIENT_SECRET = 'ad7ed1882b9148119957784e0fa24d7f'
SPOTIFY_REDIRECT_URI = 'http://localhost:8888/callback'
SCOPE = "playlist-modify-public"

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=SPOTIFY_REDIRECT_URI,
    scope=SCOPE
))



def convert_yt_to_spotify(youtube_playlist_url):
    ydl_opts = {
        'extract_flat': 'in_playlist',
        'quiet': True
    }

    with YoutubeDL(ydl_opts) as ydl:
        playlist_info = ydl.extract_info(youtube_playlist_url, download=False)

    spotify_uris = []

    for entry in playlist_info['entries']:
        track_name = entry['title']  # Title from YouTube
        results = sp.search(q=track_name, type='track', limit=1)

        if results['tracks']['items']:
            spotify_uris.append(results['tracks']['items'][0]['uri'])

    user_id = sp.me()['id']
    playlist = sp.user_playlist_create(user_id, "YouTube to Spotify", public=True)
    sp.playlist_add_items(playlist['id'], spotify_uris)

    return playlist['external_urls']['spotify']
