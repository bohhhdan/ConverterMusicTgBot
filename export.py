from pyrogram import Client, filters
from spotify_to_youtube import authenticate_youtube
from youtube_to_spotify import sp
import os

API_ID = '24032315'
API_HASH = '0febaaa3772a959ffd1007396b575353'
BOT_TOKEN = '7732427882:AAEDQOrTCxmLG4ykU18qc7zcAuqptcSfpSw'

app = Client("playlist_manager_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
user_states = {}

# Function to export playlist data to a text file named "test.txt"
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
    user_states[message.from_user.id] = None
    await message.reply(
        "🎶 Welcome to the Playlist Export Bot!\n\n"
        "Commands:\n"
        "/export_playlist - Export playlist data to a text file\n"
        "Follow instructions for the command!"
    )

@app.on_message(filters.command("export_playlist"))
async def export_playlist(_, message):
    user_states[message.from_user.id] = "awaiting_export_details"
    await message.reply(
        "Provide the platform (Spotify/YouTube) and playlist ID in this format:\n"
        "Platform, Playlist ID"
    )

@app.on_message(filters.text)
async def handle_text(_, message):
    user_id = message.from_user.id
    state = user_states.get(user_id)

    if state == "awaiting_export_details":
        try:
            platform, playlist_id = map(str.strip, message.text.split(", "))
            platform = platform.lower()

            if platform == "spotify":
                try:
                    # Fetch Spotify playlist details
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
                    # Fetch YouTube playlist details
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
    else:
        await message.reply("Please start with the /export_playlist command.")


app.run()