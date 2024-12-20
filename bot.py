from pyrogram import Client, filters
from spotify_to_youtube import authenticate_youtube, add_video_to_playlist, convert_spotify_to_yt, add_video_to_playlist_YouTube, extract_playlist_id_from_url
from youtube_to_spotify import convert_yt_to_spotify
from youtube_to_spotify import sp
from googleapiclient.errors import HttpError
import re
import os
API_ID = '24032315'
API_HASH = '0febaaa3772a959ffd1007396b575353'
BOT_TOKEN = '7618243056:AAE3bCvVPfBYSIkgIPtmF4lEcZbbn4lxHK8'

app = Client("playlist_manager_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_states = {}

def export_playlist_to_test_file(playlist_data):
    file_name = "test.txt"
    with open(file_name, "w", encoding="utf-8") as file:
        file.write("Exported Playlist Data\n")
        file.write("=" * 30 + "\n")
        for item in playlist_data:
            file.write(f"{item}\n")
    return file_name

@app.on_message(filters.command("start"))
async def start(_, message):
    user_states[message.from_user.id] = "awaiting_platform"
    await message.reply(
        "🎶 Welcome to the Playlist Converter Bot!\n\n"
        "I can help you transfer playlists between Spotify and YouTube Music.\n"
        "Please tell me:\n\n"
        "1️⃣ From which platform would you like to transfer?\n"
        "2️⃣ To which platform should I convert it?\n\n"
        "Use /convert to begin the transfer process."
        "Use /add_song or /delete_song to manage playlists."
        "/export_playlist - Export playlist data to a text file.\n"
    )


@app.on_message(filters.command("export_playlist"))
async def export_playlist(_, message):
    user_states[message.from_user.id] = "awaiting_export_details"
    await message.reply(
        "Provide the platform (Spotify/YouTube) and playlist ID in this format:\n"
        "Platform, Playlist ID"
    )
# Conversion logic
@app.on_message(filters.command("convert"))
async def convert(_, message):
    user_states[message.from_user.id] = "awaiting_conversion_platform"
    await message.reply("Which platform do you want to transfer from?\nReply with either *Spotify* or *YouTube*.")

@app.on_message(filters.text)
async def handle_text(_, message):
    user_id = message.from_user.id
    state = user_states.get(user_id, None)

    # Handle platform selection for conversion
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

    # Handle add song to playlist
    elif state == "awaiting_add_details":
        try:
            platform, playlist_id, details = message.text.split(", ")
            if platform.lower() == "youtube":
                youtube = authenticate_youtube()
                await message.reply(add_video_to_playlist_YouTube(youtube, playlist_id, details))


            elif platform.lower() == "spotify":

                try:
                    if details.startswith("https://open.spotify.com/track/"):
                        track_id = details.split("track/")[1].split("?")[0]
                        track_uri = f"spotify:track:{track_id}"
                        # Add the track directly using its URI
                        sp.playlist_add_items(playlist_id, [track_uri])
                        await message.reply("✅ Song added to Spotify playlist successfully!")

                    else:
                        results = sp.search(q=details, type="track", limit=1)
                        if results['tracks']['items']:
                            track_uri = results['tracks']['items'][0]['uri']
                            sp.playlist_add_items(playlist_id, [track_uri])
                            await message.reply("✅ Song added to Spotify playlist successfully!")
                        else:
                            await message.reply("❌ Song not found on Spotify.")

                except Exception as e:

                    await message.reply(f"❌ Failed to add song: {str(e)}")

            else:
                await message.reply("❌ Unsupported platform. Please choose either Spotify or YouTube.")
        except Exception as e:
            await message.reply(f"❌ Failed to add song: {str(e)}")

        user_states[user_id] = None
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

            elif platform == "youtube":
                try:
                    youtube = authenticate_youtube()
                    playlist_items = youtube.playlistItems().list(
                        part="snippet", playlistId=playlist_id, maxResults=50
                    ).execute()
                    tracks = [
                        f"{idx + 1}. {item['snippet']['title']}"
                        for idx, item in enumerate(playlist_items["items"])
                    ]
                    file_name = export_playlist_to_test_file(tracks)
                    await message.reply_document(file_name)
                    os.remove(file_name)
                except Exception as e:
                    await message.reply(f"❌ Failed to export YouTube playlist: {str(e)}")

            else:
                await message.reply("❌ Unsupported platform. Please choose either Spotify or YouTube.")

        except ValueError:
            await message.reply("❌ Invalid format. Use: Platform, Playlist ID")

        user_states[user_id] = None

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





    elif message.text.lower() == "/add_song":

        user_states[user_id] = "awaiting_add_details"
        await message.reply("Provide the platform (Spotify/YouTube), playlist ID, and song details in the format: \nPlatform, Playlist ID, Song/Video ID or Search Query")


    elif message.text.lower() == "/delete_song":
        user_states[user_id] = "awaiting_delete_details"
        await message.reply("Provide the platform (Spotify/YouTube), playlist ID, and song details in the format: \nPlatform, Playlist ID, Song/Video ID")

    else:
        await message.reply("Please start by using /add_song or /delete_song to manage playlists.")

# Add song to playlist
@app.on_message(filters.command("add_song"))
async def add_song(_, message):

    user_states[message.from_user.id] = "awaiting_add_details"
    await message.reply("Provide the platform (Spotify/YouTube), playlist ID, and song details in the format: \nPlatform, Playlist ID, Song/Video ID or Search Query")

# Delete song from playlist
@app.on_message(filters.command("delete_song"))
async def delete_song(_, message):

    user_states[message.from_user.id] = "awaiting_delete_details"
    await message.reply("Provide the platform (Spotify/YouTube), playlist ID, and song details in the format: \nPlatform, Playlist ID, Song/Video ID")

# Delete video from YouTube playlist
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
                    # Delete the video from the playlist
                    youtube.playlistItems().delete(id=playlist_item_id).execute()
                    return f"✅ Video deleted from YouTube playlist successfully using the URL!"
                else:
                    return "❌ Video not found in the playlist."

            except HttpError as e:
                return f"❌ Error deleting video: {str(e)}"
        else:
            return "❌ Invalid YouTube URL."

    # Case 2: If the details are a search query (no URL provided)
    else:
        try:
            # Search for the video using the details (search query)
            request = youtube.search().list(
                part="snippet",
                q=details,
                type="video",
                maxResults=1
            )
            response = request.execute()

            if response['items']:
                # Extract the video ID from the search result
                video_id = response['items'][0]['id']['videoId']

                # Now, check if this video is in the playlist
                playlist_request = youtube.playlistItems().list(
                    part="id",
                    playlistId=playlist_id,
                    videoId=video_id
                )
                playlist_response = playlist_request.execute()

                if playlist_response['items']:
                    playlist_item_id = playlist_response['items'][0]['id']
                    # Delete the video from the playlist
                    youtube.playlistItems().delete(id=playlist_item_id).execute()
                    return f"✅ Video deleted from YouTube playlist successfully using search query!"
                else:
                    return "❌ Video not found in the playlist."

            else:
                return "❌ Video not found for the given search query."
        except HttpError as e:
            return f"❌ Error during search and deletion: {str(e)}"


def extract_video_id_from_url(url):
    """Extract the video ID from a YouTube URL."""
    youtube_regex = (
        r"(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)"
    )
    match = re.match(youtube_regex, url)
    if match:
        return match.group(4)  # Return the video ID
    return None

# Remove tracks from Spotify playlist
def remove_tracks_from_spotify_playlist(playlist_id, track_uris):
    """Remove tracks from a Spotify playlist."""
    sp.playlist_remove_all_occurrences_of_items(playlist_id, track_uris)

if __name__ == "__main__":
    app.run()
