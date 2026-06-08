import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.error import TelegramError
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# إعداد السجلات (Logs) لمراقبة الأخطاء
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# 🛑 التوكن الخاص بك ثابت ومجرب 🛑
BOT_TOKEN = "8779761296:AAEkuDGAmXl2INEk6z2K2o7uvKypyuJxPkw"

# إعداد المجدول الزمني لتجنب خطأ الـ Event Loop
scheduler = AsyncIOScheduler()

# قواميس تخزين البيانات لكل مستخدم بشكل منفصل
USER_STATES = {}       
USER_CHANNELS = {}     
USER_DATA_STORE = {}   

# دالة القائمة الرئيسية للأزرار الشفافة (تم تفخيم الأزرار بالإيموجيات والترتيب)
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📢 نـشـر رسـالـة فـوريـة", callback_data="menu_publish")],
        [InlineKeyboardButton("⏰ تـنـبـيـه تـلـقـائـي (كـل سـاعـة)", callback_data="menu_auto")],
        [InlineKeyboardButton("🔄 تـغـيـيـر الـوجـهـة الـمـرتـبـطـة", callback_data="change_chat")],
    ]
    return InlineKeyboardMarkup(keyboard)

# أمر البدء /start (رسالة الترحيب وطلب الرابط بشكل فخم جداً)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    USER_STATES[user_id] = "AWAITING_CHAT_LINK"
    
    welcome_text = (
        "👑 **أهلاً بك في نظام النشر التلقائي والفوري المطور!**\n"
        "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
        "💡 **البوت مصمم لخدمة الجميع وإدارة منصاتك بذكاء.**\n\n"
        "⚙️ **خـطـوات الـتـفـعـيـل:**\n"
        "1️⃣ قم بإضافة البوت **مشرفاً (Admin)** بكامل الصلاحيات داخل (قناتك أو مجموعتك).\n"
        "2️⃣ أرسل الآن **معرف القناة/المجموعة** (مثال: `@my_channel`) أو **رابط الدعوة الخاص بها** المباشر.\n\n"
        "⏳ بانتظار إرسال الرابط أو المعرف لتجهيز لوحة التحكم الخاصة بك..."
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# معالج استقبال الرسائل (فحص روابط الدعوة والروابط العامة والمجموعات)
async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    current_state = USER_STATES.get(user_id)

    if not current_state:
        return

    # مرحلة ربط القناة أو المجموعة
    if current_state == "AWAITING_CHAT_LINK" and update.message.text:
        chat_input = update.message.text.strip()
        final_chat_id = None

        # الفحص الذكي لروابط الدعوة الخاصة المباشرة (+) واستخراج الآيدي الحقيقي لها
        if "t.me/+" in chat_input or "t.me/joinchat/" in chat_input:
            try:
                chat_details = await context.bot.get_chat(chat_id=chat_input)
                final_chat_id = chat_details.id  # الرقم الذي يبدأ بـ -100
            except Exception as e:
                logging.error(f"Error checking invite link: {e}")
                error_link_text = (
                    "❌ **عذراً، لم يتمكن النظام من قراءة رابط الدعوة الخاص!**\n"
                    "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                    "يرجى التأكد من:\n"
                    "• إضافة البوت أولاً كمسؤول (Admin) داخل المجموعة.\n"
                    "• صحة الرابط المرسل.\n\n"
                    "🔄 **أرسل الرابط الصحيح مجدداً الآن:**"
                )
                await update.message.reply_text(error_link_text, parse_mode="Markdown")
                return
        else:
            # معالجة الروابط العامة والأسماء العادية المعرفة بـ @
            if "t.me/" in chat_input:
                chat_input = "@" + chat_input.split("t.me/")[-1].replace("/", "")
            elif not chat_input.startswith("@") and not chat_input.startswith("-100"):
                chat_input = "@" + chat_input
            final_chat_id = chat_input

        # التحقق النهائي من صلاحيات المشرف وحفظ البيانات
        try:
            chat_member = await context.bot.get_chat_member(chat_id=final_chat_id, user_id=context.bot.id)
            if chat_member.status in ['administrator', 'creator']:
                USER_CHANNELS[user_id] = final_chat_id  # حفظ الآيدي الحقيقي الصافي للنشر الفعلي
                USER_STATES[user_id] = None  # تصفير الحالة
                
                success_text = (
                    "✨ **تـم الـربـط بـنـجـاح بـاهـر!**\n"
                    "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                    "🔒 تم تأمين الصلاحيات، والبوت الآن متصل ومنصتك جاهزة للنشر.\n\n"
                    "🎛️ **اختر الإجراء المطلوب من لوحة التحكم الشفافة أدناه:**"
                )
                await update.message.reply_text(success_text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
            else:
                admin_error_text = (
                    "⚠️ **تنبيه أمني: رتبة الإشراف مفقودة!**\n"
                    "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                    "البوت متواجد في الوجهة المرسلة ولكنه **ليس مشرفاً (Admin)**.\n"
                    "قم برفعه وتفعيل الصلاحيات له، ثم أرسل المعرف/الرابط مرة أخرى لإتمام الربط:"
                )
                await update.message.reply_text(admin_error_text, parse_mode="Markdown")
        except TelegramError as te:
            logging.error(f"Telegram error: {te}")
            not_found_text = (
                "🔍 **عذراً، تعذر العثور على الوجهة المحددة!**\n"
                "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                "تأكد من خطوتين أساسيتين:\n"
                "1. إضافة البوت كمشرف أولاً داخل القناة أو المجموعة.\n"
                "2. كتابة المعرف أو الرابط بشكل دقيق.\n\n"
                "✍️ **أرسل المعرف أو الرابط الصحيح الآن:**"
            )
            await update.message.reply_text(not_found_text, parse_mode="Markdown")

    # مرحلة استقبال محتوى النشر الفوري
    elif current_state == "AWAITING_PUBLISH_CONTENT":
        confirm_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ نعم، تفويض بالنشر الفوري", callback_data="confirm_publish")],
            [InlineKeyboardButton("❌ إلغاء الأمر وتراجع", callback_data="cancel_action")]
        ])

        if update.message.photo:
            photo_file_id = update.message.photo[-1].file_id
            caption = update.message.caption or ""
            USER_DATA_STORE[user_id] = {'type': 'photo', 'content': photo_file_id, 'caption': caption}
            await update.message.reply_text("❓ **هل أنت متأكد من رغبتك في نشر هذه الصورة مع النص فورا؟**", reply_markup=confirm_keyboard, parse_mode="Markdown")
        elif update.message.text:
            USER_DATA_STORE[user_id] = {'type': 'text', 'content': update.message.text}
            await update.message.reply_text("❓ **هل أنت متأكد من رغبتك في نشر هذا النص فورا؟**", reply_markup=confirm_keyboard, parse_mode="Markdown")

    # مرحلة استقبال محتوى التنبيه التلقائي
    elif current_state == "AWAITING_AUTO_CONTENT":
        if update.message.text:
            USER_DATA_STORE[user_id] = {'type': 'text', 'content': update.message.text}
            confirm_auto_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 إطلاق النشر المجدول", callback_data="confirm_auto")],
                [InlineKeyboardButton("❌ إلغاء العملية", callback_data="cancel_action")]
            ])
            await update.message.reply_text(
                f"📋 **مراجعة محتوى النشر التلقائي المتكرر (كل ساعة):**\n"
                f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                f"« {update.message.text} »\n\n"
                f"❓ **هل تود تأكيد الجدولة وإطلاق الرسالة؟**",
                reply_markup=confirm_auto_keyboard,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("⚠️ **تنبيه:** النشر المجدول المتكرر يدعم النصوص والكلمات فقط حالياً. يرجى إرسال رسالة نصية:")

# معالج ضغطات الأزرار الشفافة
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    target_chat = USER_CHANNELS.get(user_id)

    if not target_chat and query.data != "change_chat":
        await query.edit_message_text("⚠️ **خطأ في الذاكرة:** لم تقم بربط أي قناة أو مجموعة بعد. ارسل /start للبدء الجدید.", parse_mode="Markdown")
        return

    if query.data == "menu_publish":
        USER_STATES[user_id] = "AWAITING_PUBLISH_CONTENT"
        await query.edit_message_text("📥 **بانتظار المحتوى الفوري...**\nأرسل الآن الكلمات أو الصورة التي ترغب في بثها ونشرها فوراً داخل منصتك:")

    elif query.data == "confirm_publish":
        data = USER_DATA_STORE.get(user_id)
        if data:
            try:
                if data['type'] == 'text':
                    await context.bot.send_message(chat_id=target_chat, text=data['content'])
                elif data['type'] == 'photo':
                    await context.bot.send_photo(chat_id=target_chat, photo=data['content'], caption=data.get('caption', ''))
                
                await query.edit_message_text("🎯 **تم بنجاح! تم بث ونشر الرسالة في وجهتك المطلوبة فوراً.**", reply_markup=main_menu_keyboard(), parse_mode="Markdown")
            except Exception as e:
                await query.edit_message_text(f"❌ **فشل في عملية البث المباشر.** قد تكون الصلاحيات قد عُدلت. الخطأ: {e}", reply_markup=main_menu_keyboard(), parse_mode="Markdown")
            USER_DATA_STORE.pop(user_id, None)
            USER_STATES[user_id] = None

    elif query.data == "menu_auto":
        USER_STATES[user_id] = "AWAITING_AUTO_CONTENT"
        await query.edit_message_text("⏰ **بانتظار رسالة التكرار...**\nأرسل النص الذي تريد من البوت تكراره ونشره تلقائياً على رأس كل ساعة:")

    elif query.data == "confirm_auto":
        data = USER_DATA_STORE.get(user_id)
        if data and data['type'] == 'text':
            text_to_repeat = data['content']
            job_id = f"job_{user_id}"

            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)

            scheduler.add_job(
                send_hourly_msg,
                'interval',
                minutes=60,
                id=job_id,
                args=[context, target_chat, text_to_repeat]
            )

            stop_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🛑 إيقاف نظام النشر المتكرر", callback_data="stop_auto")]
            ])
            await query.edit_message_text(
                "⚡ **تم التفعيل بنجاح جبار!**\n"
                "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                "🚀 النظام الآن يجدول رسالتك وسيبثها تلقائياً كل ساعة دون توقف.\n\n"
                "👇 لإيقاف المؤقت أو تغيير الإعدادات استخدم الزر أدناه:",
                reply_markup=stop_keyboard,
                parse_mode="Markdown"
            )
            USER_STATES[user_id] = None
        else:
            await query.edit_message_text("⚠️ **حدث خطأ ما.** يرجى المحاولة مرة أخرى.", reply_markup=main_menu_keyboard(), parse_mode="Markdown")

    elif query.data == "stop_auto":
        job_id = f"job_{user_id}"
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
            await query.edit_message_text("🛑 **تم إيقاف نظام النشر المتكرر بنجاح، وتم تعطيل المؤقت الزمني.**", reply_markup=main_menu_keyboard(), parse_mode="Markdown")
        else:
            await query.edit_message_text("⚠️ **تنبيه:** لا توجد أي جدولة نشطة تعمل لحسابك في الوقت الحالي.", reply_markup=main_menu_keyboard(), parse_mode="Markdown")

    elif query.data == "cancel_action":
        USER_STATES[user_id] = None
        USER_DATA_STORE.pop(user_id, None)
        await query.edit_message_text("🔄 **تم إلغاء العملية الحالية بنجاح، والعودة إلى لوحة التحكم الرئيسية.**", reply_markup=main_menu_keyboard(), parse_mode="Markdown")

    elif query.data == "change_chat":
        USER_STATES[user_id] = "AWAITING_CHAT_LINK"
        await query.edit_message_text("📥 **تغيير الوجهة المستهدفة:**\nأرسل الآن معرف أو رابط القناة/المجموعة الجديدة التي تود ربط البوت بها:")

# الدالة التلقائية في الخلفية
async def send_hourly_msg(context: ContextTypes.DEFAULT_TYPE, chat_id: str, text: str):
    try:
        await context.bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        logging.error(f"Error in automated post: {e}")

# دالة بدء تشغيل المجدول تلقائياً فور إقلاع البوت
async def on_startup(application: Application):
    if not scheduler.running:
        scheduler.start()

# نقطة تشغيل البوت الأساسية
def main():
    app = Application.builder().token(BOT_TOKEN).post_init(on_startup).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_user_message))

    print("⚡ البوت الفخم والمستقر يعمل الآن بكفاءة 100%...")
    app.run_polling()

if __name__ == "__main__":
    main()
