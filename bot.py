import logging
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from file_converter import convert_pptx_to_pdf, convert_excel_to_pdf, images_to_pdf

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = "8715590354:AAEtfxKZ_nbeDKGApup3deLF0Pxs69gPOlg"

def get_file_size_mb(file_path):
    """Calculate file size in MB."""
    if os.path.exists(file_path):
        size_bytes = os.path.getsize(file_path)
        return round(size_bytes / (1024 * 1024), 2)
    return 0

def get_start_assets():
    text = (
        "👋 **أهلاً بك في بوت تحويل الملفات الاحترافي!**\n\n"
        "يسعدني مساعدتك في تحويل ملفاتك إلى صيغة PDF بسهولة وسرعة. 🚀\n\n"
        "📂 **ماذا يمكنني أن أفعل؟**\n"
        "• تحويل ملفات PowerPoint (`.pptx`, `.ppt`) 📊\n"
        "• تحويل ملفات Excel (`.xlsx`, `.xls`) 📈\n"
        "• دمج مجموعة صور في ملف PDF واحد 🖼\n\n"
        "✨ **كيفية الاستخدام؟**\n"
        "فقط أرسل الملف أو الصور مباشرة، وسأقوم بالباقي تلقائياً!"
    )
    keyboard = [[InlineKeyboardButton("❓ المساعدة", callback_data="help_info")]]
    return text, InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text, reply_markup = get_start_assets()
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    help_text = (
        "ℹ️ **دليل المساعدة:**\n\n"
        "1️⃣ **للملفات:** أرسل ملف البوربوينت أو الإكسل وسأرسل لك نسخة PDF فوراً.\n"
        "2️⃣ **للصور:** أرسل الصور. سأنتظر 4 ثوانٍ بعد آخر صورة لدمجها.\n"
        "3️⃣ **الأمان:** يتم حذف ملفاتك فور انتهاء عملية التحويل."
    )
    await query.edit_message_text(help_text, parse_mode="Markdown", reply_markup=get_start_assets()[1])

async def process_images(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(4)
    user_data = context.application.user_data.get(chat_id)
    if not user_data or "photo_paths" not in user_data or not user_data["photo_paths"]: return
    
    status_msg = await context.bot.send_message(chat_id, "⚙️ **جاري دمج الصور وتحويلها...**", parse_mode="Markdown")
    
    photo_paths = user_data["photo_paths"]
    user_data["photo_paths"] = []
    output_pdf_path = f"images_{chat_id}.pdf"
    
    try:
        output_pdf_path = images_to_pdf(photo_paths, output_pdf_path)
        if output_pdf_path and os.path.exists(output_pdf_path):
            await status_msg.edit_text("📤 **جاري إرسال الملف النهائي...**", parse_mode="Markdown")
            size_mb = get_file_size_mb(output_pdf_path)
            await context.bot.send_document(
                chat_id=chat_id, 
                document=open(output_pdf_path, 'rb'), 
                caption=f"✅ **تم دمج الصور بنجاح!**\n📄 **حجم الملف:** {size_mb} MB", 
                parse_mode="Markdown"
            )
            await status_msg.delete()
            os.remove(output_pdf_path)
    except Exception as e:
        await status_msg.edit_text("⚠️ **حدث خطأ أثناء دمج الصور.**")
    finally:
        for p in photo_paths:
            if os.path.exists(p): os.remove(p)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if "photo_paths" not in context.user_data: context.user_data["photo_paths"] = []
    photo_file = await update.message.photo[-1].get_file()
    photo_path = f"./{photo_file.file_id}.jpg"
    await photo_file.download_to_drive(photo_path)
    context.user_data["photo_paths"].append(photo_path)
    if "image_task" in context.user_data: context.user_data["image_task"].cancel()
    context.user_data["image_task"] = asyncio.create_task(process_images(chat_id, context))

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        document = update.message.document
        file_name = document.file_name
        if not file_name.lower().endswith(('.pptx', '.ppt', '.xlsx', '.xls')):
            await update.message.reply_text("❌ **هذا الملف غير مدعوم.** يرجى إرسال ملفات بوربوينت أو إكسل.", parse_mode="Markdown")
            return
        
        status_msg = await update.message.reply_text("📥 **جاري استلام الملف...**", parse_mode="Markdown")
        
        new_file = await context.bot.get_file(document.file_id)
        downloaded_file_path = f"./{file_name}"
        await new_file.download_to_drive(downloaded_file_path)
        
        await status_msg.edit_text("⚙️ **جاري التحويل إلى PDF...**", parse_mode="Markdown")
        
        output_pdf_path = f"{os.path.splitext(file_name)[0]}.pdf"
        if file_name.lower().endswith(('.pptx', '.ppt')):
            output_pdf_path = convert_pptx_to_pdf(downloaded_file_path, output_pdf_path)
        else:
            output_pdf_path = convert_excel_to_pdf(downloaded_file_path, output_pdf_path)
            
        if output_pdf_path and os.path.exists(output_pdf_path):
            await status_msg.edit_text("📤 **جاري إرسال الملف...**", parse_mode="Markdown")
            size_mb = get_file_size_mb(output_pdf_path)
            await update.message.reply_document(
                document=open(output_pdf_path, 'rb'), 
                caption=f"✅ **تم التحويل بنجاح!**\n📄 **حجم الملف:** {size_mb} MB", 
                parse_mode="Markdown"
            )
            await status_msg.delete()
            os.remove(output_pdf_path)
        else:
            await status_msg.edit_text("⚠️ **عذراً، حدث خطأ أثناء التحويل.**")
            
        if os.path.exists(downloaded_file_path): os.remove(downloaded_file_path)
    except Exception as e:
        logger.error(f"Error: {e}")
        if 'status_msg' in locals():
            await status_msg.edit_text("⚠️ **حدث خطأ غير متوقع.**")

async def handle_unsupported(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🤔 **يرجى إرسال ملفات بوربوينت، إكسل، أو صور فقط.**", parse_mode="Markdown")

def main() -> None:
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(help_callback, pattern="help_info"))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_unsupported))
    app.run_polling()

if __name__ == "__main__": main()
