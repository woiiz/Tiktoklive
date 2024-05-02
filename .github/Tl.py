import subprocess
import requests
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

class TikTokLiveRecorder:
    def __init__(self):
        self.room_id = None
        self.user = None
        self.http_client = requests.Session()

    def get_room_info(self, url):
        response = self.http_client.get(url)
        # Implement logic to extract user and room_id from the response HTML
        # For demonstration purposes, let's assume we have extracted user and room_id
        self.user = "example_user"
        self.room_id = "example_room_id"

    def record_live(self, update: Update, context: CallbackContext):
        if not self.room_id:
            update.message.reply_text("Room ID not found. Please call /getinfo first.")
            return
        output_file = "live_stream_record.mp4"
        command = [
            "ffmpeg",
            "-i", f"https://www.tiktok.com/@{self.user}/live/{self.room_id}",
            "-c:v", "copy",
            "-c:a", "copy",
            output_file
        ]
        subprocess.run(command)
        update.message.reply_text(f"Live stream recorded and saved as {output_file}")

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Welcome to TikTok Live Recorder Bot!\n"
        "Use /getinfo <TikTok URL> to get room info\n"
        "Use /record to start recording the live stream"
    )

def get_info(update: Update, context: CallbackContext):
    url = context.args[0]
    recorder.get_room_info(url)  # Assuming recorder is defined globally or passed as an argument
    update.message.reply_text("Room info retrieved successfully.")

def main():
    updater = Updater("6507082989:AAEpxt-hi_ZW0Li3-BtVkiy8hNYo4IgwVIc")
    dispatcher = updater.dispatcher

    global recorder
    recorder = TikTokLiveRecorder()

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("getinfo", get_info))
    dispatcher.add_handler(CommandHandler("record", recorder.record_live))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
