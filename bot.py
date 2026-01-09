from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import BadRequest
import os
from io import BytesIO
import matplotlib.pyplot as plt
from PIL import Image
from pypdf import PdfMerger

# ==================== إعدادات ====================
TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
CHANNEL_USERNAME = '@CDF991'
DEVELOPER_USERNAME = '@cdf99'
TEMPLATE_FILE = 'template.pdf'

if not TOKEN or not ADMIN_ID:
    print("خطأ: تأكد من إضافة BOT_TOKEN و ADMIN_ID في Environment Variables!")
    exit(1)

pending_users = {}
approved_users = set()
banned_users = set()
user_report_data = {}
template_exists = os.path.exists(TEMPLATE_FILE)

print("🚀 البوت شغال مع إنشاء واجهة تقرير ودمج PDF!")

def is_approved(user_id: int) -> bool:
    if user_id in banned_users:
        return False
    return user_id in approved_users or user_id == ADMIN_ID

async def check_membership(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except BadRequest:
        return False

# ==================== /start ====================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    chat_id = update.effective_chat.id

    welcome_msg = (
        "أهلا بك في بوت حساب التقييم 🎓\n\n"
        "إذا كان هنالك خطأ في عمل البوت، يمكنك التواصل مع المطور من خلال المعرف التالي: @cdf99"
    )
    await update.message.reply_text(welcome_msg)

    if user_id == ADMIN_ID:
        approved_users.add(ADMIN_ID)
        keyboard = [
            [InlineKeyboardButton("رفع نموذج", callback_data="upload_template"),
             InlineKeyboardButton("حذف النموذج", callback_data="delete_template")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("👑 يا هلا يا صاحب البوت! البوت شغال 100% 🚀\nاستخدم الأزرار لإدارة النموذج:", reply_markup=reply_markup)
        return

    if user_id in banned_users:
        await update.message.reply_text("🚫 أنت محظور من استخدام البوت. تواصل مع @cdf99")
        return

    if not await check_membership(context, user_id):
        keyboard = [[InlineKeyboardButton("انضم إلى قناة المطور", url="https://t.me/CDF991")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("⚠️ لاستخدام البوت، يجب عليك الانضمام أولاً إلى قناة المطور:\n@CDF991", reply_markup=reply_markup)
        return

    if is_approved(user_id):
        await update.message.reply_text("🎓 مرحباً مرة ثانية! اكتب /report لإنشاء واجهة تقريرك 📚")
        return

    if user_id not in pending_users:
        pending_users[user_id] = {
            'name': user.full_name,
            'username': user.username or "لا يوجد",
            'chat_id': chat_id
        }

        keyboard = [
            [InlineKeyboardButton("✅ موافقة", callback_data=f"approve_{user_id}"),
             InlineKeyboardButton("❌ رفض", callback_data=f"reject_{user_id}"),
             InlineKeyboardButton("🚫 حظر", callback_data=f"ban_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        admin_text = f"""
🔔 *طلب جديد للانضمام*

👤 الاسم: {user.full_name}
@{user.username if user.username else "لا يوجد"}
🔢 ID: `{user_id}`
        """

        try:
            await context.bot.send_message(ADMIN_ID, admin_text, parse_mode='Markdown', reply_markup=reply_markup)
        except BadRequest:
            print("خطأ في إرسال الإشعار")

    await update.message.reply_text("⏳ تم إرسال طلبك للموافقة، انتظر الرد قريبًا 🕐")

# ==================== /report ====================
async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_approved(user_id):
        await update.message.reply_text("🚫 لازم تكون موافق عليك أولاً")
        return

    if not await check_membership(context, user_id):
        keyboard = [[InlineKeyboardButton("انضم إلى القناة", url="https://t.me/CDF991")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🚫 غادرت القناة! انضم مرة أخرى @CDF991", reply_markup=reply_markup)
        return

    if not template_exists:
        await update.message.reply_text("⚠️ لا يوجد نموذج محمل حاليًا. تواصل مع المطور @cdf99")
        return

    user_report_data[user_id] = {
        'step': 'university_logo',
        'university_logo': None,
        'college_logo': None,
        'university_name': '',
        'college_name': '',
        'department_name': '',
        'report_title': '',
        'student_name': '',
        'stage': '',
        'group': '',
        'supervisor': '',
        'date': '',
    }

    keyboard = [[InlineKeyboardButton("تخطي", callback_data="skip_university_logo")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🖼️ يرجى رفع شعار الجامعة (صورة). أو اضغط تخطي:", reply_markup=reply_markup)

# ==================== معالجة الرسائل والصور ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_approved(user_id):
        return

    if not await check_membership(context, user_id):
        keyboard = [[InlineKeyboardButton("انضم إلى القناة", url="https://t.me/CDF991")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🚫 غادرت القناة! انضم مرة أخرى للاستمرار @CDF991", reply_markup=reply_markup)
        return

    if user_id not in user_report_data:
        await update.message.reply_text("⚠️ ابدأ من جديد بـ /report")
        return

    state = user_report_data[user_id]
    text = update.message.text if update.message.text else None
    photo = update.message.photo[-1] if update.message.photo else None
    document = update.message.document if update.message.document else None

    if state['step'] == 'university_logo':
        if photo or (document and document.mime_type.startswith('image/')):
            file = photo.get_file() if photo else document.get_file()
            state['university_logo'] = await file
            state['step'] = 'college_logo'
            keyboard = [[InlineKeyboardButton("تخطي", callback_data="skip_college_logo")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("🖼️ يرجى رفع شعار الكلية (إن وجد). أو اضغط تخطي:", reply_markup=reply_markup)
        else:
            await update.message.reply_text("❌ يرجى رفع صورة فقط لشعار الجامعة.")

    elif state['step'] == 'college_logo':
        if photo or (document and document.mime_type.startswith('image/')):
            file = photo.get_file() if photo else document.get_file()
            state['college_logo'] = await file
            state['step'] = 'university_name'
            await update.message.reply_text("🏫 أدخل اسم الجامعة (عربي أو إنجليزي):")
        else:
            await update.message.reply_text("❌ يرجى رفع صورة فقط لشعار الكلية.")

    elif state['step'] == 'university_name':
        state['university_name'] = text
        state['step'] = 'college_name'
        await update.message.reply_text("🏫 أدخل اسم الكلية (عربي أو إنجليزي):")

    elif state['step'] == 'college_name':
        state['college_name'] = text
        state['step'] = 'department_name'
        keyboard = [[InlineKeyboardButton("تخطي", callback_data="skip_department_name")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🏛️ أدخل اسم القسم العلمي (إن وجد). أو اضغط تخطي:", reply_markup=reply_markup)

    elif state['step'] == 'department_name':
        state['department_name'] = text
        state['step'] = 'report_title'
        await update.message.reply_text("📄 أدخل عنوان التقرير:")

    elif state['step'] == 'report_title':
        state['report_title'] = text
        state['step'] = 'student_name'
        await update.message.reply_text("👤 أدخل الاسم الثلاثي:")

    elif state['step'] == 'student_name':
        state['student_name'] = text
        state['step'] = 'stage'
        await update.message.reply_text("🎓 أدخل المرحلة:")

    elif state['step'] == 'stage':
        state['stage'] = text
        state['step'] = 'group'
        keyboard = [[InlineKeyboardButton("تخطي", callback_data="skip_group")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🔤 أدخل حرف الكروب (إن وجد). أو اضغط تخطي:", reply_markup=reply_markup)

    elif state['step'] == 'group':
        state['group'] = text
        state['step'] = 'supervisor'
        await update.message.reply_text("👨‍🏫 أدخل اسم المشرف (الدكتور):")

    elif state['step'] == 'supervisor':
        state['supervisor'] = text
        state['step'] = 'date'
        await update.message.reply_text("📅 أدخل تاريخ التقديم (سنة أو يوم-شهر-سنة):")

    elif state['step'] == 'date':
        state['date'] = text
        await generate_cover(update, context, user_id)

# ==================== إنشاء الواجهة ودمج PDF ====================
async def generate_cover(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    state = user_report_data[user_id]

    fig, ax = plt.subplots(figsize=(8.5, 11))
    ax.axis('off')

    if state['university_logo']:
        logo_bytes = await state['university_logo'].download_as_bytearray()
        logo_img = Image.open(BytesIO(logo_bytes))
        ax.imshow(logo_img, extent=[6, 8.5, 9, 11], aspect='preserve')

    if state['college_logo']:
        logo_bytes = await state['college_logo'].download_as_bytearray()
        logo_img = Image.open(BytesIO(logo_bytes))
        ax.imshow(logo_img, extent=[0, 2.5, 9, 11], aspect='preserve')

    ax.text(0.5, 0.95, state['university_name'], transform=ax.transAxes, ha='center', fontsize=16, fontweight='bold')
    ax.text(0.5, 0.9, state['college_name'], transform=ax.transAxes, ha='center', fontsize=14)
    if state['department_name']:
        ax.text(0.5, 0.85, state['department_name'], transform=ax.transAxes, ha='center', fontsize=12)

    ax.text(0.5, 0.6, state['report_title'], transform=ax.transAxes, ha='center', fontsize=18, fontweight='bold')

    ax.text(0.5, 0.4, state['student_name'], transform=ax.transAxes, ha='center', fontsize=14)
    ax.text(0.5, 0.35, f"المرحلة: {state['stage']}", transform=ax.transAxes, ha='center', fontsize=12)
    if state['group']:
        ax.text(0.5, 0.3, f"الكروب: {state['group']}", transform=ax.transAxes, ha='center', fontsize=12)
    ax.text(0.5, 0.25, f"إشراف: {state['supervisor']}", transform=ax.transAxes, ha='center', fontsize=12)
    ax.text(0.5, 0.2, f"التاريخ: {state['date']}", transform=ax.transAxes, ha='center', fontsize=12)

    cover_buffer = BytesIO()
    fig.savefig(cover_buffer, format='pdf', bbox_inches='tight', pad_inches=0)
    plt.close(fig)
    cover_buffer.seek(0)

    merger = PdfMerger()
    merger.append(TEMPLATE_FILE)
    merger.append(cover_buffer)
    output_buffer = BytesIO()
    merger.write(output_buffer)
    merger.close()
    output_buffer.seek(0)

    await context.bot.send_document(chat_id=user_id, document=output_buffer, filename="واجهة_التقرير.pdf", caption="✅ تم إنشاء الواجهة بنجاح!")

    keyboard = [
        [InlineKeyboardButton("نعم، دمج مع التقرير", callback_data="merge_report"),
         InlineKeyboardButton("لا شكراً", callback_data="no_merge")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("هل تريد دمج الواجهة مع ملف التقرير الكامل؟", reply_markup=reply_markup)

    del user_report_data[user_id]

# ==================== معالجة الأزرار ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = query.from_user.id

    if data.startswith("skip_"):
        skip_step = data[5:]
        user_report_data[user_id]['step'] = skip_step.replace("skip_", "")
        await query.edit_message_text("✅ تم التخطي، تابع الخطوة التالية.")

    elif data == "merge_report":
        user_report_data[user_id] = {'step': 'upload_report', 'cover_buffer': None}
        await query.edit_message_text("🗂️ ارفع ملف التقرير الكامل (PDF) للدمج مع الواجهة.")

    elif data == "no_merge":
        await query.edit_message_text("✅ تمام، شكراً لاستخدام البوت!")

    # معالجة طلبات الموافقة والحظر (زي ما كان)

# ==================== main ====================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("report", report_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO | filters.DOCUMENT, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 البوت جاهز لإنشاء واجهات تقارير جامعية!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
