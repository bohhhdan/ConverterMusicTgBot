import re
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from yt_dlp import YoutubeDL
from google.auth.exceptions import RefreshError
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
import os

SPOTIFY_CLIENT_ID = 'bbef9944f39449c2b689b2db4a0a0d1c'
SPOTIFY_CLIENT_SECRET = 'ad7ed1882b9148119957784e0fa24d7f'
SPOTIFY_REDIRECT_URI = 'http://localhost:8888/callback'

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]


def search_youtube_videos(youtube, query, max_results=5):
    """Search for videos on YouTube and return multiple results."""
    try:
        request = youtube.search().list(
            part="snippet",
            q=query,
            type="video",
            maxResults=max_results
        )
        response = request.execute()
        return response['items']
    except Exception as e:
        print(f"Error searching videos: {str(e)}")
        return []


def convert_spotify_to_yt(spotify_playlist_url):
    try:
        playlist_id = extract_playlist_id(spotify_playlist_url)
    except ValueError as e:
        return str(e)

    results = sp.playlist_tracks(playlist_id)
    youtube = authenticate_youtube()
    yt_playlist_id = create_youtube_playlist(youtube)
    youtube_urls = []

    for item in results['items']:
        track = item['track']
        query = f"{track['name']} {track['artists'][0]['name']}"

        # Search for videos
        videos = search_youtube_videos(youtube, query)
        if videos:
            # Display options
            print(f"\nFound multiple matches for: {query}")
            for idx, video in enumerate(videos[:5], 1):
                print(f"{idx}. {video['snippet']['title']} - {video['snippet']['channelTitle']}")

            # Get user selection
            while True:
                try:
                    selection = int(input("Select a video (1-5): "))
                    if 1 <= selection <= len(videos):
                        selected_video = videos[selection - 1]
                        video_id = selected_video['id']['videoId']
                        add_video_to_playlist(youtube, yt_playlist_id, video_id)
                        youtube_urls.append(f"https://www.youtube.com/watch?v={video_id}")
                        print(f"✅ Added: {selected_video['snippet']['title']}")
                        break
                    else:
                        print("❌ Invalid selection. Please try again.")
                except ValueError:
                    print("❌ Please enter a valid number.")

    return f"https://www.youtube.com/playlist?list={yt_playlist_id}"
def authenticate_youtube():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                creds = None  # Reset creds to force re-authentication

        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
            creds = flow.run_local_server(port=0)
            with open("token.json", "w") as token_file:
                token_file.write(creds.to_json())

    if not creds or not creds.valid:
        raise Exception("Failed to authenticate YouTube API: Authorization required.")

    youtube = build("youtube", "v3", credentials=creds)
    return youtube


def create_youtube_playlist(youtube, title="Converted Spotify Playlist", description="Playlist created by the bot"):
    request = youtube.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "tags": ["Music", "Converted"],
                "defaultLanguage": "en"
            },
            "status": {
                "privacyStatus": "private"
            }
        }
    )
    response = request.execute()
    return response["id"]

def add_video_to_playlist(youtube, playlist_id, video_id):
    request = youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": video_id
                }
            }
        }
    )
    request.execute()


def add_video_to_playlist(youtube, playlist_id, video_id):
    request = youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": video_id
                }
            }
        }
    )
    request.execute()


def extract_playlist_id_from_url(url):

    match = re.search(r'(?:list=)([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    return None



def add_video_to_playlist_YouTube(youtube, playlist_id, details):
    playlist_id = extract_playlist_id_from_url(playlist_id)
    if "youtube.com/watch?v=" in details or "youtu.be/" in details:
        video_id = extract_video_id_from_url(details)
        if video_id:
            try:
                request = youtube.playlistItems().insert(
                    part="snippet",
                    body={
                        "snippet": {
                            "playlistId": playlist_id,
                            "resourceId": {
                                "kind": "youtube#video",
                                "videoId": video_id
                            }
                        }
                    }
                )
                request.execute()
                return f"✅ Video added to YouTube playlist successfully using the URL!"
            except HttpError as e:
                return f"❌ Error adding video: {str(e)}"
        else:
            return "❌ Invalid YouTube URL."

    # Case 2: If the details are a search query (no URL provided)
    else:
        try:

            request = youtube.search().list(
                part="snippet",
                q=details,
                type="video",
                maxResults=1
            )
            response = request.execute()

            if response['items']:
                video_id = response['items'][0]['id']['videoId']


                request = youtube.playlistItems().insert(
                    part="snippet",
                    body={
                        "snippet": {
                            "playlistId": playlist_id,
                            "resourceId": {
                                "kind": "youtube#video",
                                "videoId": video_id
                            }
                        }
                    }
                )
                request.execute()
                return f"✅ Video added to YouTube playlist successfully using search query!"
            else:
                return "❌ Video not found for the given search query."
        except HttpError as e:
            return f"❌ Error during search and addition: {str(e)}"



def extract_video_id_from_url(url):
    youtube_regex = (
        r"(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)"
    )
    match = re.match(youtube_regex, url)
    if match:
        return match.group(4)
    return None

def extract_playlist_id(spotify_url):
    match = re.search(r"playlist/([A-Za-z0-9]+)", spotify_url)
    if match:
        return match.group(1)
    else:
        raise ValueError("Invalid Spotify playlist URL.")

def convert_spotify_to_yt(spotify_playlist_url):
    try:
        playlist_id = extract_playlist_id(spotify_playlist_url)
    except ValueError as e:
        return str(e)

    results = sp.playlist_tracks(playlist_id)
    youtube = authenticate_youtube()  
    yt_playlist_id = create_youtube_playlist(youtube) 
    youtube_urls = []

    ydl_opts = {
        'quiet': True,
        'format': 'bestaudio/best',
        'noplaylist': True,
        'ignoreerrors': True
    }

    for item in results['items']:
        track = item['track']
        query = f"{track['name']} {track['artists'][0]['name']}"

        with YoutubeDL(ydl_opts) as ydl:
            try:
                search_results = ydl.extract_info(f"ytsearch:{query}", download=False)['entries']
                if search_results:
                    video_id = search_results[0]['id']
                    add_video_to_playlist(youtube, yt_playlist_id, video_id)  
                    youtube_urls.append(f"https://www.youtube.com/watch?v={video_id}")
            except Exception as e:
                print(f"Error fetching YouTube URL for {query}: {e}")

    return f"https://www.youtube.com/playlist?list={yt_playlist_id}"