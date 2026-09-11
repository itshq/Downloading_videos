import os
import re
import threading
from urllib.parse import urlparse
import telebot
import yt_dlp
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8929993717:AAF46J7Dbx9IDD2J7WKr9Nsgb73NAK5R-Vo"

bot = telebot.TeleBot(TOKEN)

DOWNLOAD_FOLDER = "downloads"
if not os.path.exists(DOWNLOAD_FOLDER):
  os.makedirs(DOWNLOAD_FOLDER)

SUPPORTED_DOMAINS = [
    "tiktok.com",
    "vm.tiktok.com",
    "youtube.com",
    "youtu.be",
    "instagram.com",
    "instagr.am",
    "pinterest.com",
    "pin.it",
]


def is_supported_url(url: str) -> bool:
  parsed = urlparse(url)
  return any(domain in parsed.netloc for domain in SUPPORTED_DOMAINS)


def get_platform(url: str) -> str:
  parsed = urlparse(url)
  if "tiktok" in parsed.netloc:
    return "TikTok"
  elif "youtube" in parsed.netloc or "youtu.be" in parsed.netloc:
    return "YouTube"
  elif "instagram" in parsed.netloc:
    return "Instagram"
  elif "pinterest" in parsed.netloc or "pin.it" in parsed.netloc:
    return "Pinterest"
  return "Unknown"


def get_ydl_opts(platform: str) -> dict:
  base_opts = {
      "quiet": True,
      "no_warnings": True,
      "extract_flat": False,
      "outtmpl": os.path.join(DOWNLOAD_FOLDER, "%(title)s_%(id)s.%(ext)s"),
  }

  if platform == "TikTok":
    base_opts.update({
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
    })

  elif platform == "YouTube":
    base_opts.update({
        "format": (
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        ),
        "merge_output_format": "mp4",
    })

  elif platform == "Instagram":
    base_opts.update({
        "format": "best",
    })

  elif platform == "Pinterest":
    base_opts.update({
        "format": "best[ext=mp4]/best",
    })

  return base_opts


def download_video(url: str, chat_id: int) -> tuple:
  platform = get_platform(url)
  if platform == "Unknown":
    return None, None, "❌ المنصة غير مدعومة"

  opts = get_ydl_opts(platform)

  try:
    with yt_dlp.YoutubeDL(opts) as ydl:
      info = ydl.extract_info(url, download=True)

      if "entries" in info:
        filename = ydl.prepare_filename(info["entries"][0])
      else:
        filename = ydl.prepare_filename(info)

      if not os.path.exists(filename):
        base = os.path.splitext(filename)[0]
        if os.path.exists(base + ".mp4"):
          filename = base + ".mp4"
        elif os.path.exists(base + ".mkv"):
          filename = base + ".mkv"
        elif os.path.exists(base + ".webm"):
          filename = base + ".webm"

      if os.path.exists(filename):
        return filename, platform, None
      else:
        return None, None, "❌ فشل في العثور على الملف المحمل"

  except Exception as e:
    return None, None, f"❌ خطأ في التحميل: {str(e)[:100]}"


def clean_temp_files():
  for file in os.listdir(DOWNLOAD_FOLDER):
    file_path = os.path.join(DOWNLOAD_FOLDER, file)
    try:
      if os.path.isfile(file_path):
        os.remove(file_path)
    except:
      pass


@bot.message_handler(commands=["start"])
def start_command(message):
  image_url = "https://l.top4top.io/p_3904xk9im1.jpg"
  
  markup = InlineKeyboardMarkup(row_width=2)
  markup.add(
      InlineKeyboardButton("🎵 تيك توك", callback_data="platform_tiktok", style="primary"),
      InlineKeyboardButton("📺 يوتيوب", callback_data="platform_youtube", style="primary"),
      InlineKeyboardButton("📸 انستغرام", callback_data="platform_instagram", style="primary"),
      InlineKeyboardButton("📌 بنترست", callback_data="platform_pinterest", style="primary")
  )
  markup.add(InlineKeyboardButton("👨‍💻 المطور", url="https://t.me/its_h_q", style="danger"))
  
  try:
    bot.send_photo(
        message.chat.id,
        image_url,
        reply_markup=markup
    )
  except Exception:
    bot.reply_to(message, "أهلاً بك، أرسل الرابط مباشرة:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("platform_"))
def callback_platforms(call):
  platform_key = call.data.split("_")[1]
  platform_names_ar = {
      "tiktok": "تيك توك",
      "youtube": "يوتيوب",
      "instagram": "انستغرام",
      "pinterest": "بنترست"
  }
  platform_name = platform_names_ar.get(platform_key, platform_key)
  
  image_url = "https://l.top4top.io/p_3904xk9im1.jpg"
  caption_text = f"📥 أرسل رابط *{platform_name}* الآن لكي أقوم بتحميله لك:"
  
  try:
    bot.send_photo(
        call.message.chat.id,
        image_url,
        caption=caption_text,
        parse_mode="Markdown"
    )
  except Exception:
    bot.send_message(
        call.message.chat.id,
        caption_text,
        parse_mode="Markdown"
    )
    
  bot.answer_callback_query(call.id)


@bot.message_handler(commands=["help"])
def help_command(message):
  help_text = "أرسل رابط الفيديو مباشرة وسيتم تحميله."
  bot.reply_to(message, help_text)


@bot.message_handler(commands=["clean"])
def clean_command(message):
  clean_temp_files()
  bot.reply_to(message, "🧹 تم الحذف")


@bot.message_handler(func=lambda message: True)
def handle_message(message):
  text = message.text.strip()
  chat_id = message.chat.id

  if not text.startswith(("http://", "https://")):
    bot.reply_to(message, "❌ أرسل رابط صحيح")
    return

  if not is_supported_url(text):
    bot.reply_to(message, "❌ الرابط غير مدعوم")
    return

  status_msg = bot.reply_to(message, "📥 جاري التحميل...")

  def download_and_send():
    try:
      filename, platform, error = download_video(text, chat_id)

      if error or not filename:
        bot.edit_message_text(
            error or "❌ فشل التحميل",
            chat_id,
            status_msg.message_id,
        )
        return

      with open(filename, "rb") as video_file:
        bot.send_video(
            chat_id,
            video_file,
            timeout=60,
        )

      bot.delete_message(chat_id, status_msg.message_id)

      try:
        os.remove(filename)
      except:
        pass

    except Exception as e:
      bot.edit_message_text(
          f"❌ حدث خطأ: {str(e)[:100]}",
          chat_id,
          status_msg.message_id,
      )

  thread = threading.Thread(target=download_and_send)
  thread.start()


if __name__ == "__main__":
  print("✅ البوت يعمل...")
  clean_temp_files()
  bot.infinity_polling(timeout=60)
