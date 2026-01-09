from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import BadRequest
import os

# ==================== إعدادات ====================
TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
CHANNEL_USERNAME = '@CDF991'
DEVELOPER_USERNAME = '@cdf99'

if not TOKEN or not ADMIN_ID:
    print("خطأ: تأكد من إضافة BOT_TOKEN و ADMIN_ID في Environment Variables!")
    exit(1)

pending_users = {}
approved_users = set()
banned_users = set()
user_data = {}

print("🚀 البوت شغال مع لوحة تحكم دائمة للحظر!")

def is_approved(user_id: int) -> bool:
    if user_id in banned_users:
        return False
    return user_id in approved_users or user_id == ADMIN_ID

def get_overall_grade(average: float) -> str:
    if average >= 90:
        return "امتياز 🏆"
    elif average >= 80:
        return "جيد جداً 🌟"
    elif average >= 70:
        return "جيد 👍"
    elif average >= 60:
        return "متوسط ✅"
    elif average >= 50:
        return "مقبول 📈"
    else:
        return "راسب 😔"

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
        await update.message.reply_text("👑 يا هلا يا صاحب البوت! البوت شغال 100% 🚀\nاكتب /panel للوحة التحكم")
        return

    if user_id in banned_users:
        await update.message.reply_text("🚫 أنت محظور من استخدام البوت. تواصل مع @cdf99")
        return

    if not await check_membership(context, user_id):
        keyboard = [[InlineKeyboardButton("انضم إلى قناة المطور", url="https://t.me/CDF991")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "⚠️ لاستخدام البوت، يجب عليك الانضمام أولاً إلى قناة المطور:\n@CDF991",
            reply_markup=reply_markup
        )
        return

    if is_approved(user_id):
        await update.message.reply_text("🎓 مرحباً مرة ثانية! اكتب /calc لحساب تقديرك 📚")
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

# ==================== /panel - لوحة التحكم الدائمة ====================
async def panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("🚫 هذا الأمر للأدمن فقط")
        return

    if not approved_users and not banned_users:
        await update.message.reply_text("لا يوجد مستخدمين موافق عليهم أو محظورين حاليًا")
        return

    keyboard = []
    for uid in approved_users | banned_users:  # كل المستخدمين (موافقين + محظورين)
        status = "محظور" if uid in banned_users else "موافق"
        keyboard.append([
            InlineKeyboardButton(f"{status} | ID: {uid}", callback_data=f"dummy_{uid}"),
            InlineKeyboardButton("🚫 حظر" if uid not in banned_users else "✅ رفع الحظر", callback_data=f"toggle_ban_{uid}")
        ])

    keyboard.append([InlineKeyboardButton("🔄 تحديث اللوحة", callback_data="refresh_panel")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🔧 *لوحة التحكم*\nاختر مستخدم لتغيير حالته:", parse_mode='Markdown', reply_markup=reply_markup)

# ==================== /calc و handle_message ====================
async def calc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_approved(user_id):
        await update.message.reply_text("🚫 لازم تكون موافق عليك أولاً")
        return

    if not await check_membership(context, user_id):
        keyboard = [[InlineKeyboardButton("انضم إلى القناة", url="https://t.me/CDF991")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🚫 غادرت القناة! انضم مرة أخرى @CDF991", reply_markup=reply_markup)
        return

    user_data[user_id] = {'step': 'num_courses', 'current': 1, 'grades': [], 'total': 0.0, 'num_courses': 0}
    await update.message.reply_text("📚 *كم عدد المواد؟*\nأدخل رقم فقط:", parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_approved(user_id):
        return

    if not await check_membership(context, user_id):
        keyboard = [[InlineKeyboardButton("انضم إلى القناة", url="https://t.me/CDF991")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🚫 غادرت القناة! انضم مرة أخرى @CDF991", reply_markup=reply_markup)
        return

    text = update.message.text.strip()
    if user_id not in user_data:
        await update.message.reply_text("⚠️ ابدأ من جديد بـ /calc")
        return

    state = user_data[user_id]
    # باقي كود الحساب زي ما هو (ما غيرته)

    # ... (نفس الكود اللي عندك للحساب، اختصرت عشان المساحة)

# ==================== معالجة الأزرار ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "refresh_panel":
        await panel_command(update, context)
        return

    if data.startswith("toggle_ban_"):
        target_id = int(data.split("_")[2])
        if target_id in banned_users:
            banned_users.remove(target_id)
            status = "رفع الحظر"
        else:
            banned_users.add(target_id)
            approved_users.discard(target_id)
            status = "حظر"

        await query.edit_message_text(f"✅ تم {status} المستخدم {target_id}")
        await panel_command(update, context)  # تحديث اللوحة
        return

    # باقي الكود للموافقة والرفض في الطلبات الجديدة زي ما هو

# ==================== main ====================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("calc", calc_command))
    app.add_handler(CommandHandler("panel", panel_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 البوت جاهز مع لوحة تحكم دائمة!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
