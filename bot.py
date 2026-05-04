import logging
import os
import asyncio
import time
import json
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from file_converter import convert_file, images_to_pdf, compress_pdf, url_to_pdf, shorten_url

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN", "8715590354:AAEtfxKZ_nbeDKGApup3deLF0Pxs69gPOlg")
STATS_FILE = "bot_stats.json"

# Supported formats and their conversion targets
CONVERSION_MAP = {
    # Images
    "png": ["jpg", "pdf", "webp", "bmp", "tiff", "gif", "ico"],
    "jpg": ["png", "pdf", "webp", "bmp", "tiff", "gif", "ico"],
    "jpeg": ["png", "pdf", "webp", "bmp", "tiff", "gif", "ico"],
    "webp": ["png", "jpg", "pdf", "bmp", "tiff", "gif"],
    "bmp": ["png", "jpg", "pdf", "webp", "tiff"],
    "tiff": ["png", "jpg", "pdf", "webp", "bmp"],
    "tif": ["png", "jpg", "pdf", "webp", "bmp"],
    "gif": ["png", "jpg", "pdf", "webp", "mp4"],
    "ico": ["png", "jpg", "pdf"],
    "heic": ["png", "jpg", "pdf", "webp"],
    "svg": ["png", "jpg", "pdf"],
    "psd": ["png", "jpg", "pdf"],
    "eps": ["png", "jpg", "pdf"],
    # Audio
    "mp3": ["ogg", "wav", "flac", "aac", "m4a", "opus"],
    "ogg": ["mp3", "wav", "flac", "aac", "m4a"],
    "opus": ["mp3", "ogg", "wav", "flac", "aac"],
    "wav": ["mp3", "ogg", "flac", "aac", "m4a", "opus"],
    "flac": ["mp3", "ogg", "wav", "aac", "m4a"],
    "wma": ["mp3", "ogg", "wav", "flac", "aac"],
    "m4a": ["mp3", "ogg", "wav", "flac", "aac"],
    "aac": ["mp3", "ogg", "wav", "flac", "m4a"],
    "aiff": ["mp3", "ogg", "wav", "flac", "aac"],
    "amr": ["mp3", "ogg", "wav"],
    # Video
    "mp4": ["avi", "mkv", "webm", "mov", "gif", "mp3"],
    "avi": ["mp4", "mkv", "webm", "mov", "gif", "mp3"],
    "wmv": ["mp4", "mkv", "webm", "mov", "mp3"],
    "mkv": ["mp4", "avi", "webm", "mov", "gif", "mp3"],
    "3gp": ["mp4", "avi", "mkv", "webm", "mp3"],
    "3gpp": ["mp4", "avi", "mkv", "webm", "mp3"],
    "mpg": ["mp4", "avi", "mkv", "webm", "mp3"],
    "mpeg": ["mp4", "avi", "mkv", "webm", "mp3"],
    "webm": ["mp4", "avi", "mkv", "mov", "gif", "mp3"],
    "ts": ["mp4", "avi", "mkv", "webm", "mp3"],
    "mov": ["mp4", "avi", "mkv", "webm", "gif", "mp3"],
    "flv": ["mp4", "avi", "mkv", "webm", "mp3"],
    "vob": ["mp4", "avi", "mkv", "webm", "mp3"],
    # Documents
    "docx": ["pdf", "txt", "odt", "rtf"],
    "doc": ["pdf", "txt", "odt", "rtf"],
    "xlsx": ["pdf", "csv", "ods"],
    "xls": ["pdf", "csv", "ods"],
    "txt": ["pdf", "docx"],
    "rtf": ["pdf", "docx", "txt"],
    "odt": ["pdf", "docx", "txt"],
    "ods": ["pdf", "xlsx", "csv"],
    "csv": ["pdf", "xlsx"],
    "html": ["pdf", "txt"],
    # Presentations
    "pptx": ["pdf", "odp"],
    "ppt": ["pdf", "odp"],
    "pptm": ["pdf", "odp"],
    "pps": ["pdf", "odp"],
    "ppsx": ["pdf", "odp"],
    "odp": ["pdf", "pptx"],
    # PDF
    "pdf": ["docx", "txt", "jpg", "png"],
    # eBooks
    "epub": ["pdf", "mobi", "txt"],
    "mobi": ["pdf", "epub", "txt"],
    "fb2": ["pdf", "epub", "txt"],
    "djvu": ["pdf"],
    # Subtitles
    "srt": ["vtt", "ass", "txt"],
    "vtt": ["srt", "ass", "txt"],
    "ass": ["srt", "vtt", "txt"],
    "ssa": ["srt", "vtt", "txt"],
    "sub": ["srt", "vtt", "txt"],
}

IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff', '.tif', '.gif', '.ico', '.heic', '.svg', '.psd', '.eps')

def get_supported_count():
    total_formats = len(CONVERSION_MAP)
    total_conversions = sum(len(v) for v in CONVERSION_MAP.values())
    return total_formats, total_conversions

# --- Stats ---
def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r') as f:
            return json.load(f)
    return {"total_users": [], "total_files": 0}

def save_stats(stats):
    with open(STATS_FILE, 'w') as f:
        json.dump(stats, f)

def update_user_stats(user_id):
    stats = load_stats()
    if user_id not in stats["total_users"]:
        stats["total_users"].append(user_id)
    stats["total_files"] += 1
    save_stats(stats)

def get_file_size_mb(file_path):
    if os.path.exists(file_path):
        size = os.path.getsize(file_path)
        if size < 1024 * 1024:
            return f"{round(size / 1024, 1)} KB"
        return f"{round(size / (1024 * 1024), 2)} MB"
    return "0"

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_formats, total_conversions = get_supported_count()
    welcome = (
        "📁 **أرسل لي ملف لتحويله.**\n"
        f"_{total_formats} صيغة مدعومة:_\n\n"
        "🖼 **Images (17)**\n"
        "PNG, JPG, JPEG, WEBP, BMP, TIF, TIFF, GIF, ICO, HEIC, SVG, PSD, EPS\n\n"
        "🎵 **Audio (11)**\n"
        "MP3, OGG, OPUS, WAV, FLAC, WMA, M4A, AAC, AIFF, AMR\n\n"
        "🎬 **Video (14)**\n"
        "MP4, AVI, WMV, MKV, 3GP, MPEG, WEBM, TS, MOV, FLV, VOB\n\n"
        "📄 **Document (10)**\n"
        "XLSX, XLS, TXT, RTF, DOC, DOCX, ODT, PDF, ODS, CSV\n\n"
        "📊 **Presentation (7)**\n"
        "PPT, PPTX, PPTM, PPS, PPSX, ODP\n\n"
        "📚 **eBook (5)**\n"
        "EPUB, MOBI, FB2, DJVU\n\n"
        "💬 **Subtitle (5)**\n"
        "SRT, VTT, ASS, SSA, SUB\n\n"
        f"_{total_conversions} عملية تحويل مدعومة_\n\n"
"✨ **ميزات إضافية:**\n"
        "• دمج صور → PDF (أرسل صور متعددة)\n"
        "• ضغط PDF\n"
        "• تحويل روابط → PDF\n"
        "• اختصار روابط\n\n"
        "🔗 لاختصار رابط أرسل: /short الرابط"
    )
    await update.message.reply_text(welcome, parse_mode="Markdown")

async def process_images(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(4)
    user_data = context.application.user_data.get(chat_id)
    if not user_data or "photo_paths" not in user_data or not user_data["photo_paths"]:
        return
    
    photo_paths = list(user_data["photo_paths"])
    user_data["photo_paths"] = []
    
    if len(photo_paths) == 1:
        # صورة واحدة - نعطيه خيارات تحويل
        ext = os.path.splitext(photo_paths[0])[1].lower().strip('.')
        if not ext:
            ext = "jpg"
        targets = CONVERSION_MAP.get(ext, ["pdf", "png", "jpg"])
        keyboard = []
        row = []
        for t in targets:
            row.append(InlineKeyboardButton(f"📄 {t.upper()}", callback_data=f"conv|{photo_paths[0]}|{t}"))
            if len(row) == 3:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        
        await context.bot.send_message(
            chat_id,
            f"🖼 **صورة واحدة** | اختر الصيغة المطلوبة:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return
    
    # عدة صور - ندمجهم بـ PDF
    status_msg = await context.bot.send_message(chat_id, "⚙️ جاري دمج الصور في PDF...", parse_mode="Markdown")
    
    try:
        start_time = time.time()
        path = images_to_pdf(photo_paths, f"merged_{chat_id}.pdf")
        if path:
            compressed = compress_pdf(path, f"final_merged_{chat_id}.pdf")
            duration = round(time.time() - start_time, 2)
            size = get_file_size_mb(compressed)
            
            await context.bot.send_document(
                chat_id=chat_id,
                document=open(compressed, 'rb'),
                caption=f"✅ تم دمج {len(photo_paths)} صور → PDF\n📊 الحجم: {size} | ⏱ {duration}s",
                parse_mode="Markdown"
            )
            update_user_stats(chat_id)
            await status_msg.delete()
            for f in [path, compressed]:
                if os.path.exists(f): os.remove(f)
        else:
            await status_msg.edit_text("⚠️ حدث خطأ أثناء الدمج.")
    except Exception as e:
        logger.error(f"Image merge error: {e}")
        await status_msg.edit_text("⚠️ حدث خطأ أثناء الدمج.")
    finally:
        for p in photo_paths:
            if os.path.exists(p): os.remove(p)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if "photo_paths" not in context.user_data:
        context.user_data["photo_paths"] = []
    
    file = await update.message.photo[-1].get_file()
    path = f"./photo_{chat_id}_{int(time.time()*1000)}.jpg"
    await file.download_to_drive(path)
    context.user_data["photo_paths"].append(path)
    
    if "image_task" in context.user_data and not context.user_data["image_task"].done():
        context.user_data["image_task"].cancel()
    context.user_data["image_task"] = asyncio.create_task(process_images(chat_id, context))

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    doc = update.message.document
    name = doc.file_name if doc.file_name else "file"
    ext = os.path.splitext(name)[1].lower().strip('.')
    
    # Download file
    file = await context.bot.get_file(doc.file_id)
    input_path = f"./{chat_id}_{int(time.time())}_{name}"
    await file.download_to_drive(input_path)
    
    # If image sent as document, add to merge queue
    if ext in ('jpg', 'jpeg', 'png', 'webp', 'bmp', 'tiff', 'tif'):
        if "photo_paths" not in context.user_data:
            context.user_data["photo_paths"] = []
        context.user_data["photo_paths"].append(input_path)
        if "image_task" in context.user_data and not context.user_data["image_task"].done():
            context.user_data["image_task"].cancel()
        context.user_data["image_task"] = asyncio.create_task(process_images(chat_id, context))
        return
    
    # Check if format is supported
    if ext not in CONVERSION_MAP:
        await update.message.reply_text(f"❌ صيغة `.{ext}` غير مدعومة حالياً.", parse_mode="Markdown")
        if os.path.exists(input_path): os.remove(input_path)
        return
    
    # Show conversion options
    targets = CONVERSION_MAP[ext]
    keyboard = []
    row = []
    for t in targets:
        row.append(InlineKeyboardButton(f"{t.upper()}", callback_data=f"conv|{input_path}|{t}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    # PDF special options
    if ext == "pdf":
        keyboard.append([
            InlineKeyboardButton("📉 ضغط", callback_data=f"compress|{input_path}")
        ])
    
    await update.message.reply_text(
        f"📁 **{name}** ({get_file_size_mb(input_path)})\nاختر الصيغة المطلوبة:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    data = query.data.split("|")
    
    if data[0] == "conv":
        input_path = data[1]
        target_format = data[2]
        
        if not os.path.exists(input_path):
            await query.edit_message_text("⚠️ الملف لم يعد متاحاً. أرسله مرة أخرى.")
            return
        
        await query.edit_message_text(f"⚙️ جاري التحويل إلى {target_format.upper()}...")
        
        start_time = time.time()
        output_path = convert_file(input_path, target_format)
        duration = round(time.time() - start_time, 2)
        
        if output_path and os.path.exists(output_path):
            size = get_file_size_mb(output_path)
            await context.bot.send_document(
                chat_id=chat_id,
                document=open(output_path, 'rb'),
                caption=f"✅ تم التحويل → {target_format.upper()}\n📊 {size} | ⏱ {duration}s"
            )
            update_user_stats(chat_id)
            if os.path.exists(output_path): os.remove(output_path)
        else:
            await context.bot.send_message(chat_id, "⚠️ فشل التحويل. تأكد من أن الملف سليم.")
        
        if os.path.exists(input_path): os.remove(input_path)
    
    elif data[0] == "compress":
        input_path = data[1]
        if not os.path.exists(input_path):
            await query.edit_message_text("⚠️ الملف لم يعد متاحاً.")
            return
        
        await query.edit_message_text("📉 جاري ضغط PDF...")
        orig_size = get_file_size_mb(input_path)
        output_path = compress_pdf(input_path, f"compressed_{os.path.basename(input_path)}")
        new_size = get_file_size_mb(output_path)
        
        await context.bot.send_document(
            chat_id=chat_id,
            document=open(output_path, 'rb'),
            caption=f"✅ تم الضغط\n📏 قبل: {orig_size} → بعد: {new_size}"
        )
        update_user_stats(chat_id)
        if os.path.exists(output_path): os.remove(output_path)
        if os.path.exists(input_path): os.remove(input_path)
    


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    chat_id = update.effective_chat.id
    

    # Check if URL - convert to PDF
    url_pattern = re.compile(r'https?://[^\s]+')
    if url_pattern.match(text):
        status = await update.message.reply_text("🌐 جاري تحويل الرابط إلى PDF...")
        path = url_to_pdf(text, f"url_{chat_id}.pdf")
        if path and os.path.exists(path):
            size = get_file_size_mb(path)
            await context.bot.send_document(chat_id=chat_id, document=open(path, 'rb'), caption=f"✅ تم تحويل الرابط → PDF\n📊 {size}")
            update_user_stats(chat_id)
            if os.path.exists(path): os.remove(path)
        else:
            await status.edit_text("⚠️ فشل تحويل الرابط.")
        await status.delete()
        return
    
    # Otherwise
    await update.message.reply_text("📁 أرسل لي ملف أو صورة لتحويله، أو رابط لتحويله إلى PDF.\n\n🔗 لاختصار رابط: /short الرابط")

async def handle_short(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("🔗 أرسل الرابط بعد الأمر:\n`/short https://example.com`", parse_mode="Markdown")
        return
    
    url = context.args[0]
    status = await update.message.reply_text("🔗 جاري اختصار الرابط...")
    short = shorten_url(url)
    if short:
        await status.edit_text(f"✅ الرابط المختصر:\n\n🔗 {short}")
    else:
        await status.edit_text("⚠️ فشل اختصار الرابط. تأكد من صحته.")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("short", handle_short))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
