from pyrogram import Client, filters
from spotify_to_youtube import authenticate_youtube, add_video_to_playlist, convert_spotify_to_yt, add_video_to_playlist_YouTube
from youtube_to_spotify import convert_yt_to_spotify
from youtube_to_spotify import sp
from googleapiclient.errors import HttpError
import re
API_ID = '24032315'
API_HASH = '0febaaa3772a959ffd1007396b575353'
BOT_TOKEN = '7732427882:AAEDQOrTCxmLG4ykU18qc7zcAuqptcSfpSw'

app = Client("playlist_manager_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_states = {}

# Handle starting of the bot with instructions
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

    # Conversion from Spotify to YouTube
    elif state == "awaiting_spotify_link":
        spotify_link = message.text
        try:
            yt_link = convert_spotify_to_yt(spotify_link)
            user_states[user_id] = None
            await message.reply(f"✅ Your playlist is ready! Here is your YouTube Music link:\n{yt_link}")
        except Exception as e:
            await message.reply(f"❌ Error during conversion: {str(e)}")

    # Conversion from YouTube to Spotify
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
                add_video_to_playlist_YouTube(youtube, playlist_id, details)
                await message.reply("✅ Video added to YouTube playlist successfully!")


            elif platform.lower() == "spotify":

                try:

                    # Check if 'details' contains a valid Spotify URI

                    if details.startswith("https://open.spotify.com/track/"):

                        # Extract the track ID from the URL

                        track_id = details.split("track/")[1].split("?")[0]

                        track_uri = f"spotify:track:{track_id}"

                        # Add the track directly using its URI

                        sp.playlist_add_items(playlist_id, [track_uri])

                        await message.reply("✅ Song added to Spotify playlist successfully!")

                    else:

                        # If 'details' is not a valid Spotify track URL, perform a search

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

    # Handle delete song from playlist
    elif state == "awaiting_delete_details":
        try:
            platform, playlist_id, details = message.text.split(", ")

            if platform.lower() == "youtube":
                youtube = authenticate_youtube()
                delete_video_from_youtube_playlist(youtube, playlist_id, details)
                await message.reply("✅ Video deleted from YouTube playlist successfully!")

            elif platform.lower() == "spotify":
                try:
                    # Check if 'details' contains a valid Spotify track URL
                    if details.startswith("https://open.spotify.com/track/"):
                        # Extract track ID and delete
                        track_id = details.split("track/")[1].split("?")[0]
                        track_uri = f"spotify:track:{track_id}"
                        sp.playlist_remove_all_occurrences_of_items(playlist_id, [track_uri])
                        await message.reply("✅ Song deleted from Spotify playlist successfully!")
                    else:
                        # Search for the song if it's not a valid URL
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




    # Handle add song to playlist
    elif message.text.lower() == "/add_song":

        user_states[user_id] = "awaiting_add_details"
        await message.reply("Provide the platform (Spotify/YouTube), playlist ID, and song details in the format: \nPlatform, Playlist ID, Song/Video ID or Search Query")

    # Handle delete song from playlist
    elif message.text.lower() == "/delete_song":
        user_states[user_id] = "awaiting_delete_details"
        await message.reply("Provide the platform (Spotify/YouTube), playlist ID, and song details in the format: \nPlatform, Playlist ID, Song/Video ID")

    else:
        await message.reply("Please start by using /add_song or /delete_song to manage playlists.")

# Add song to playlist
@app.on_message(filters.command("add_song"))
async def add_song(_, message):
    """Add a song to a playlist on Spotify or YouTube."""
    user_states[message.from_user.id] = "awaiting_add_details"
    await message.reply("Provide the platform (Spotify/YouTube), playlist ID, and song details in the format: \nPlatform, Playlist ID, Song/Video ID or Search Query")

# Delete song from playlist
@app.on_message(filters.command("delete_song"))
async def delete_song(_, message):
    """Delete a song from a playlist on Spotify or YouTube."""
    user_states[message.from_user.id] = "awaiting_delete_details"
    await message.reply("Provide the platform (Spotify/YouTube), playlist ID, and song details in the format: \nPlatform, Playlist ID, Song/Video ID")

# Delete video from YouTube playlist
def delete_video_from_youtube_playlist(youtube, playlist_id, details):
    """Delete a video from a YouTube playlist by URL or by search query."""

    # Case 1: If the details contain a valid YouTube URL
    if "youtube.com/watch?v=" in details or "youtu.be/" in details:
        video_id = extract_video_id_from_url(details)
        if video_id:
            try:
                # First, check if the video exists in the playlist
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
