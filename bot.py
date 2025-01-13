from pyrogram import Client, filters
from spotify_to_youtube import authenticate_youtube, add_video_to_playlist_YouTube, convert_spotify_to_yt
from youtube_to_spotify import convert_yt_to_spotify, sp
from googleapiclient.errors import HttpError
import os
import re

API_ID = '24032315'
API_HASH = '0febaaa3772a959ffd1007396b575353'
BOT_TOKEN = '7618243056:AAE3bCvVPfBYSIkgIPtmF4lEcZbbn4lxHK8'

app = Client("playlist_manager_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_states = {}
user_data = {}

def extract_video_id_from_url(url):
    youtube_regex = (
        r"(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)"
    )
    match = re.match(youtube_regex, url)
    if match:
        return match.group(4)
    return None

def export_playlist_to_test_file(playlist_data):
    file_name = "test.txt"
    with open(file_name, "w", encoding="utf-8") as file:
        file.write("Exported Playlist Data\n")
        file.write("=" * 30 + "\n")
        for item in playlist_data:
            file.write(f"{item}\n")
    return file_name

def extract_playlist_id_from_url(url):
    """Extract the playlist ID from a YouTube playlist URL."""
    match = re.search(r"(?:list=)([a-zA-Z0-9_-]+)", url)
    if match:
        return match.group(1)
    else:
        raise ValueError("Invalid YouTube playlist URL.")

def delete_video_from_youtube_playlist(youtube, playlist_id, details):
    playlist_id = extract_playlist_id_from_url(playlist_id)
    if "youtube.com/watch?v=" in details or "youtu.be/" in details:
        video_id = extract_video_id_from_url(details)
        if video_id:
            try:
                request = youtube.playlistItems().list(
                    part="id",
                    playlistId=playlist_id,
                    videoId=video_id
                )
                response = request.execute()

                if response['items']:
                    playlist_item_id = response['items'][0]['id']
                    youtube.playlistItems().delete(id=playlist_item_id).execute()
                    return f"✅ Video deleted from YouTube playlist successfully using the URL!"
                else:
                    return "❌ Video not found in the playlist."

            except HttpError as e:
                return f"❌ Error deleting video: {str(e)}"
        else:
            return "❌ Invalid YouTube URL."
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
                playlist_request = youtube.playlistItems().list(
                    part="id",
                    playlistId=playlist_id,
                    videoId=video_id
                )
                playlist_response = playlist_request.execute()

                if playlist_response['items']:
                    playlist_item_id = playlist_response['items'][0]['id']
                    youtube.playlistItems().delete(id=playlist_item_id).execute()
                    return f"✅ Video deleted from YouTube playlist successfully using search query!"
                else:
                    return "❌ Video not found in the playlist."

            else:
                return "❌ Video not found for the given search query."
        except HttpError as e:
            return f"❌ Error during search and deletion: {str(e)}"

@app.on_message(filters.command("start"))
async def start(_, message):
    user_states[message.from_user.id] = "awaiting_platform"
    await message.reply(
        "🎶 Welcome to the Playlist Converter Bot!\n\n"
        "I can help you transfer playlists between Spotify and YouTube Music.\n"
        "Please tell me:\n\n"
        "1️⃣ From which platform would you like to transfer?\n"
        "2️⃣ To which platform should I convert it?\n\n"
        "Use /convert to begin the transfer process.\n"
        "Use /add_song or /delete_song to manage playlists.\n"
        "/export_playlist - Export playlist data to a text file.\n"
    )

@app.on_message(filters.command("convert"))
async def convert(_, message):
    user_states[message.from_user.id] = "awaiting_conversion_platform"
    await message.reply("Which platform do you want to transfer from?\nReply with either *Spotify* or *YouTube*.")

@app.on_message(filters.command("export_playlist"))
async def export_playlist(_, message):
    user_states[message.from_user.id] = "awaiting_export_details"
    await message.reply(
        "Provide the platform (Spotify/YouTube) and playlist ID in this format:\n"
        "Platform, Playlist ID"
    )

@app.on_message(filters.command("add_song"))
async def add_song(_, message):
    user_states[message.from_user.id] = "awaiting_add_details"
    await message.reply("Provide the platform (Spotify/YouTube), playlist ID, and song details in the format: \nPlatform, Playlist ID, Song/Video ID or Search Query")

@app.on_message(filters.command("delete_song"))
async def delete_song(_, message):
    user_states[message.from_user.id] = "awaiting_delete_details"
    await message.reply("Provide the platform (Spotify/YouTube), playlist ID, and song details in the format: \nPlatform, Playlist ID, Song/Video ID")

@app.on_message(filters.text)
async def handle_text(_, message):
    user_id = message.from_user.id
    state = user_states.get(user_id)

    if state == "awaiting_conversion_platform":
        if message.text.lower() == "spotify":
            user_states[user_id] = "awaiting_spotify_link"
            await message.reply("Great! Now, paste the Spotify playlist link:")

        elif message.text.lower() == "youtube":
            user_states[user_id] = "awaiting_youtube_link"
            await message.reply("Awesome! Now, paste the YouTube playlist link:")

        else:
            await message.reply("❌ Sorry, I didn't understand. Please reply with either *Spotify* or *YouTube*.")

    elif state == "awaiting_spotify_link":
        spotify_link = message.text
        try:
            yt_link = convert_spotify_to_yt(spotify_link)
            user_states[user_id] = None
            await message.reply(f"✅ Your playlist is ready! Here is your YouTube Music link:\n{yt_link}")
        except Exception as e:
            await message.reply(f"❌ Error during conversion: {str(e)}")

    elif state == "awaiting_youtube_link":
        youtube_link = message.text
        try:
            spotify_link = convert_yt_to_spotify(youtube_link)
            user_states[user_id] = None
            await message.reply(f"✅ Your playlist is ready! Here is your Spotify link:\n{spotify_link}")
        except Exception as e:
            await message.reply(f"❌ Error during conversion: {str(e)}")

    elif state == "awaiting_export_details":
        try:
            platform, playlist_id = map(str.strip, message.text.split(", "))
            platform = platform.lower()

            if platform == "spotify":
                try:
                    playlist = sp.playlist(playlist_id)
                    tracks = [
                        f"{idx + 1}. {track['track']['name']} - {track['track']['artists'][0]['name']}"
                        for idx, track in enumerate(playlist["tracks"]["items"])
                    ]
                    file_name = export_playlist_to_test_file(tracks)
                    await message.reply_document(file_name)
                    os.remove(file_name)
                except Exception as e:
                    await message.reply(f"❌ Failed to export Spotify playlist: {str(e)}")



    elif state == "awaiting_delete_details":
        try:
            platform, playlist_id, details = message.text.split(", ")
            if platform.lower() == "youtube":
                youtube = authenticate_youtube()
                await message.reply(delete_video_from_youtube_playlist(youtube, playlist_id, details))

            elif platform.lower() == "spotify":
                try:
                    if details.startswith("https://open.spotify.com/track/"):
                        track_id = details.split("track/")[1].split("?")[0]
                        track_uri = f"spotify:track:{track_id}"
                        sp.playlist_remove_all_occurrences_of_items(playlist_id, [track_uri])
                        await message.reply("✅ Song deleted from Spotify playlist successfully!")
                    else:
                        results = sp.search(q=details, type="track", limit=1)
                        if results['tracks']['items']:
                            track_uri = results['tracks']['items'][0]['uri']
                            sp.playlist_remove_all_occurrences_of_items(playlist_id, [track_uri])
                            await message.reply("✅ Song deleted from Spotify playlist successfully!")
                        else:
                            await message.reply("❌ Song not found on Spotify.")
                except Exception as e:
                    await message.reply(f"❌ Failed to delete song: {str(e)}")

            user_states[user_id] = None

        except Exception as e:
            await message.reply(f"❌ Failed to delete song: {str(e)}")

    elif state == "awaiting_add_details":
        try:
            platform, playlist_id, details = message.text.split(", ")
            if platform.lower() == "youtube":
                playlist_id = extract_playlist_id_from_url(playlist_id)
                youtube = authenticate_youtube()
                request = youtube.search().list(
                    part="snippet",
                    q=details,
                    type="video",
                    maxResults=5
                )
                response = request.execute()


            elif platform.lower() == "spotify":
                try:
                    if details.startswith("https://open.spotify.com/track/"):
                        track_id = details.split("track/")[1].split("?")[0]
                        track_uri = f"spotify:track:{track_id}"
                        sp.playlist_add_items(playlist_id, [track_uri])
                        await message.reply("✅ Song added to Spotify playlist successfully!")
                    else:
                        results = sp.search(q=details, type="track", limit=5)
                        if results['tracks']['items']:
                            user_data[user_id] = {
                                "tracks": results['tracks']['items'],
                                "playlist_id": playlist_id
                            }
                            user_states[user_id] = "awaiting_track_selection"

                            options_text = "Found multiple tracks. Please select one by sending its number (1-5):\n\n"
                            for idx, track in enumerate(results['tracks']['items'], 1):
                                title = track['name']
                                artist = track['artists'][0]['name']
                                options_text += f"{idx}. {title} - {artist}\n"
                            await message.reply(options_text)
                        else:
                            await message.reply("❌ No tracks found on Spotify.")
                except Exception as e:
                    await message.reply(f"❌ Failed to add song: {str(e)}")

        except Exception as e:
            await message.reply(f"❌ Failed to process request: {str(e)}")

    elif state == "awaiting_video_selection":
        try:
            selection = int(message.text)
            if user_id in user_data and 1 <= selection <= 5:
                videos = user_data[user_id]["videos"]
                selected_video = videos[selection - 1]
                video_id = selected_video['id']['videoId']
                playlist_id = user_data[user_id]["playlist_id"]

                youtube = authenticate_youtube()
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
                    await message.reply(f"✅ Added: {selected_video['snippet']['title']}")
                except Exception as e:
                    await message.reply(f"❌ Error adding video: {str(e)}")

                del user_data[user_id]
                user_states[user_id] = None
            else:
                await message.reply("❌ Please select a valid number between 1 and 5.")
        except ValueError:
            await message.reply("❌ Please enter a valid number.")
        except Exception as e:
            await message.reply(f"❌ Error processing selection: {str(e)}")

    elif state == "awaiting_track_selection":
        try:
            selection = int(message.text)
            if user_id in user_data and 1 <= selection <= 5:
                tracks = user_data[user_id]["tracks"]
                selected_track = tracks[selection - 1]
                track_uri = selected_track['uri']
                playlist_id = user_data[user_id]["playlist_id"]

                try:
                    sp.playlist_add_items(playlist_id, [track_uri])
                    await message.reply(f"✅ Added: {selected_track['name']} - {selected_track['artists'][0]['name']}")
                except Exception as e:
                    await message.reply(f"❌ Error adding track: {str(e)}")

                del user_data[user_id]
                user_states[user_id] = None
            else:
                await message.reply("❌ Please select a valid number between 1 and 5.")
        except ValueError:
            await message.reply("❌ Please enter a valid number.")
        except Exception as e:
            await message.reply(f"❌ Error processing selection: {str(e)}")

    else:
        await message.reply("Please start by using /add_song or /delete_song to manage playlists.")

if __name__ == "__main__":
    app.run()
