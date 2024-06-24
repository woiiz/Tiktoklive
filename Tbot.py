import subprocess
import requests
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext

class TikTokLiveRecorder:
    def __init__(self):
        self.room_id = None
        self.user = None
        self.process = None
        self.http_client = requests.Session()

    def get_room_info(self, url):
        response = self.http_client.get(url)
        # Implement logic to extract user and room_id from the response HTML
        # For demonstration purposes, let's assume we have extracted user and room_id
        self.user = "example_user"
        self.room_id = "example_room_id"

    async def record_live(self, update: Update, context: CallbackContext):
        if not self.room_id:
            await update.message.reply_text("Room ID not found. Please call /getinfo first.")
            return
        output_file = "live_stream_record.mp4"
        command = [
            "ffmpeg",
            "-i", f"https://www.tiktok.com/@{self.user}/live/{self.room_id}",
            "-c:v", "copy",
            "-c:a", "copy",
            output_file
        ]
        try:
            self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = self.process.communicate()
            print("FFmpeg output:", stdout.decode())
            print("FFmpeg errors:", stderr.decode())
            if os.path.exists(output_file):
                await update.message.reply_text(f"Recording started. Use /stop to stop recording.")
            else:
                await update.message.reply_text("Recording failed. Please check logs for details.")
        except Exception as e:
            await update.message.reply_text(f"Error starting recording: {str(e)}")

    async def stop_recording(self, update: Update, context: CallbackContext):
        if self.process:
            self.process.terminate()
            self.process.wait()
            stdout, stderr = self.process.communicate()
            print("FFmpeg output:", stdout.decode())
            print("FFmpeg errors:", stderr.decode())
            self.process = None

            if os.path.exists("live_stream_record.mp4"):
                await update.message.reply_text("Recording stopped.")
                await self.upload_video(update, context, "live_stream_record.mp4")
            else:
                await update.message.reply_text("Recording stopped, but no video file was created.")
        else:
            await update.message.reply_text("No recording in progress.")

    async def upload_video(self, update: Update, context: CallbackContext, file_path: str):
        with open(file_path, 'rb') as video_file:
            await context.bot.send_video(chat_id=update.message.chat_id, video=video_file)
        await update.message.reply_text("Video uploaded to Telegram.")

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Welcome to TikTok Live Recorder Bot!\n"
        "Use /getinfo <TikTok URL> to get room info\n"
        "Use /record to start recording the live stream\n"
        "Use /stop to stop recording the live stream"
    )

async def get_info(update: Update, context: CallbackContext):
    url = context.args[0]
    recorder.get_room_info(url)  # Assuming recorder is defined globally or passed as an argument
    await update.message.reply_text("Room info retrieved successfully.")

def main():
    application = Application.builder().token("7180683439:AAF_XxCr3dYvcb6gVKXRPNnD1rbdZZ7OQQ4").build()

    global recorder
    recorder = TikTokLiveRecorder()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("getinfo", get_info))
    application.add_handler(CommandHandler("record", recorder.record_live))
    application.add_handler(CommandHandler("stop", recorder.stop_recording))

    application.run_polling()

if __name__ == "__main__":
    main()
