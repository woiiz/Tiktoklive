import os
import re
import time
import threading
import urllib.parse
import html
import subprocess
import requests
from datetime import datetime
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# === Configuration ===
TELEGRAM_TOKEN = "7922252254:AAFgzW7IcyS04zmiDvH32ibTLIb9vcTE1KI" or "YOUR_BOT_TOKEN"
AUTHORIZED_USER_ID = 931426871
# ======================

# Global state
waiting_for = {}
active_recordings = []
record_id_counter = 1

# === Utility functions ===

def find_data_url(text):
    match = re.search(r'data:application/vnd\.apple\.mpegurl,[^"\'>\s]+', text)
    return match.group(0) if match else None

def decode_data_url(data_url):
    prefix = "data:application/vnd.apple.mpegurl,"
    if data_url.startswith(prefix):
        encoded_url = data_url[len(prefix):]
        return urllib.parse.unquote(encoded_url)
    return None

def fetch_and_decode_stream(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers, timeout=10)
    res.raise_for_status()
    content = html.unescape(res.text)
    data_url = find_data_url(content)
    return decode_data_url(data_url) if data_url else None

def extract_streamer_name(m3u8_url):
    parsed = urllib.parse.urlparse(m3u8_url)
    path = parsed.path.split("/")
    for part in reversed(path):
        if part and '.' not in part:
            return part
    return "host"

# === Bot Handlers ===

def start(update: Update, context: CallbackContext):
    update.message.reply_text("Welcome! Use /decode, /record, /stop <id>, /status.")

def decode_command(update: Update, context: CallbackContext):
    if update.message.from_user.id != AUTHORIZED_USER_ID:
        return
    waiting_for[update.message.from_user.id] = 'decode'
    update.message.reply_text("Send me the page URL or `data:` stream link.")

def record_command(update: Update, context: CallbackContext):
    if update.message.from_user.id != AUTHORIZED_USER_ID:
        return
    waiting_for[update.message.from_user.id] = 'record'
    update.message.reply_text("Send the `.m3u8` stream link to begin recording.")

def stop_command(update: Update, context: CallbackContext):
    if update.message.from_user.id != AUTHORIZED_USER_ID:
        return
    args = context.args
    if not args:
        update.message.reply_text("Usage: /stop <id>")
        return
    try:
        target_id = int(args[0])
    except ValueError:
        update.message.reply_text("Invalid ID.")
        return

    for rec in active_recordings:
        if rec["id"] == target_id:
            rec["process"].terminate()
            update.message.reply_text(f"Stopped recording ID {target_id}. Uploading video soon...")
            return
    update.message.reply_text(f"No recording found with ID {target_id}.")

def status_command(update: Update, context: CallbackContext):
    if update.message.from_user.id != AUTHORIZED_USER_ID:
        return
    if not active_recordings:
        update.message.reply_text("No active recordings.")
        return
    msg = "Active Recordings:\n"
    for rec in active_recordings:
        mins, secs = divmod(int(time.time() - rec["start_time"].timestamp()), 60)
        msg += f"{rec['id']}: {rec['streamer']} - {rec['start_time'].strftime('%H:%M:%S')} ({mins}m {secs}s)\n"
    update.message.reply_text(msg)

def handle_message(update: Update, context: CallbackContext):
    global record_id_counter
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    if user_id != AUTHORIZED_USER_ID:
        return

    mode = waiting_for.get(user_id)
    bot = Bot(token=TELEGRAM_TOKEN)

    if mode == 'decode':
        try:
            decoded = decode_data_url(text) if text.startswith("data:") else fetch_and_decode_stream(text)
            update.message.reply_text(f"Decoded link:\n{decoded}" if decoded else "No stream link found.")
        except Exception as e:
            update.message.reply_text(f"Decode error: {e}")
        waiting_for.pop(user_id, None)

    elif mode == 'record':
        m3u8_link = text
        record_id = record_id_counter
        record_id_counter += 1
        start_time = datetime.now()
        streamer = extract_streamer_name(m3u8_link)
        filename = f"record_{record_id}_{streamer}.mp4"

        def record():
            try:
                process = subprocess.Popen(
                    ["ffmpeg", "-y", "-i", m3u8_link, "-c", "copy", filename],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )

                active_recordings.append({
                    "id": record_id,
                    "user_id": user_id,
                    "process": process,
                    "file": filename,
                    "start_time": start_time,
                    "streamer": streamer,
                })

                time.sleep(5)
                if process.poll() is not None:
                    bot.send_message(chat_id=user_id, text="Recording failed. Host may have ended their live or stream is unreachable.")
                    active_recordings[:] = [r for r in active_recordings if r["id"] != record_id]
                    return

                process.wait()

                if os.path.exists(filename):
                    duration = datetime.now() - start_time
                    mins, secs = divmod(int(duration.total_seconds()), 60)
                    caption = f"Recording done.\nDuration: {mins}m {secs}s\nStreamer: {streamer}"
                    with open(filename, 'rb') as f:
                        bot.send_video(chat_id=user_id, video=f, caption=caption)
            except Exception as e:
                bot.send_message(chat_id=user_id, text=f"Recording failed: {e}")
            finally:
                active_recordings[:] = [r for r in active_recordings if r["id"] != record_id]
                if os.path.exists(filename):
                    os.remove(filename)

        update.message.reply_text(f"Recording started for {streamer} (ID: {record_id})...")
        threading.Thread(target=record).start()
        waiting_for.pop(user_id, None)

# === Main bot setup ===

def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("decode", decode_command))
    dp.add_handler(CommandHandler("record", record_command))
    dp.add_handler(CommandHandler("stop", stop_command))
    dp.add_handler(CommandHandler("status", status_command))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
