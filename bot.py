from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import BadRequest
import os

# ==================== إعدادات ====================
TOKEN = os.getenv('8233989883:AAG1GFekQEOq_uhmJWwGvPCV5FXiGQ_f2To')          # ياخذ التوكن من المتغيرات في Render
ADMIN_ID = int(os.getenv('ADMIN_ID'))

if not TOKEN or not ADMIN_ID:
    print("خطأ: تأكد من إضافة BOT_TOKEN و ADMIN_ID في Environment Variables!")
    exit(1)
    
pending_users = {}
approved_users = set()
user_data = {}  # لتخزين بيانات الحساب (عدد المواد، الدرجات، إلخ)

print("🚀 البوت شغال كامل مع حساب التقدير!")

def is_approved(user_id: int) -> bool:
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

# ==================== /start ====================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    chat_id = update.effective_chat.id

    if user_id == ADMIN_ID:
        approved_users.add(ADMIN_ID)
        await update.message.reply_text(
            "👑 يا هلا يا صاحب البوت!\nالبوت شغال 100% 🚀\nجرب /calc عشان تحسب تقديرك"
        )
        return

    if is_approved(user_id):
        await update.message.reply_text(
            "🎓 مرحباً مرة ثانية!\nاكتب /calc لحساب تقديرك الجامعي 📚"
        )
        return

    if user_id not in pending_users:
        pending_users[user_id] = {
            'name': user.full_name,
            'username': user.username or "لا يوجد",
            'chat_id': chat_id
        }

        keyboard = [
            [InlineKeyboardButton("✅ موافقة", callback_data=f"approve_{user_id}"),
             InlineKeyboardButton("❌ رفض", callback_data=f"reject_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        admin_text = f"""
🔔 *طلب جديد!*

👤 الاسم: {user.full_name}
@{user.username if user.username else "لا يوجد"}
🔢 ID: `{user_id}`
        """

        try:
            await context.bot.send_message(ADMIN_ID, admin_text, parse_mode='Markdown', reply_markup=reply_markup)
        except BadRequest:
            print("خطأ: ما قدرت أرسل للأدمن")

    await update.message.reply_text(
        "⏳ طلبك وصل لصاحب البوت.\nانتظر شوية وراح يجيك الرد 🕐"
    )

# ==================== /calc ====================
async def calc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_approved(user_id):
        await update.message.reply_text("🚫 لازم تكون موافق عليك أولاً عشان تستخدم /calc")
        return

    user_data[user_id] = {
        'step': 'num_courses',
        'current': 1,
        'grades': [],
        'total': 0.0,
        'num_courses': 0
    }

    await update.message.reply_text(
        "📚 *كم عدد المواد هذا الفصل؟*\n\nأدخل رقم فقط (مثال: 6)",
        parse_mode='Markdown'
    )

# ==================== معالجة الرسائل النصية (الأهم!) ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_approved(user_id):
        return  # يتجاهل غير الموافقين

    text = update.message.text.strip()

    if user_id not in user_data:
        await update.message.reply_text("⚠️ ابدأ من جديد بـ /calc")
        return

    state = user_data[user_id]

    if state['step'] == 'num_courses':
        if text.isdigit() and int(text) > 0:
            state['num_courses'] = int(text)
            state['step'] = 'enter_grade'
            await update.message.reply_text(
                f"📖 *المادة 1 من {state['num_courses']}*\n\nأدخل الدرجة (0-100):",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ أدخل رقم صحيح أكبر من 0")

    elif state['step'] == 'enter_grade':
        try:
            grade = float(text)
            if 0 <= grade <= 100:
                state['grades'].append(grade)
                state['total'] += grade

                if state['current'] >= state['num_courses']:
                    # حساب النتيجة النهائية
                    average = state['total'] / state['num_courses']
                    overall = get_overall_grade(average)

                    result = f"""
🎉 *النتيجة جاهزة يا بطل!*

📊 المعدل: *{average:.2f}*
🏅 التقدير العام: *{overall}*

📋 تفاصيل الدرجات:
"""
                    for i, g in enumerate(state['grades'], 1):
                        result += f"• المادة {i}: {g}\n"

                    result += "\n✨ لحساب جديد: /calc"

                    await update.message.reply_text(result, parse_mode='Markdown')
                    del user_data[user_id]  # تنظيف البيانات
                else:
                    state['current'] += 1
                    await update.message.reply_text(f"✅ تم حفظ درجة المادة {state['current']-1}")
                    await update.message.reply_text(
                        f"📖 *المادة {state['current']} من {state['num_courses']}*\nأدخل الدرجة:",
                        parse_mode='Markdown'
                    )
            else:
                await update.message.reply_text("❌ الدرجة لازم تكون بين 0 و 100")
        except ValueError:
            await update.message.reply_text("❌ أدخل رقم صحيح مثل: 85 أو 92.5")

# ==================== الأزرار (موافقة/رفض) ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = int(data.split("_")[1])
    action = "موافقة" if "approve" in data else "رفض"

    if user_id not in pending_users:
        await query.edit_message_text("⚠️ الطلب تم معالجته من قبل")
        return

    info = pending_users.pop(user_id)

    if action == "موافقة":
        approved_users.add(user_id)
        user_msg = "✅ *مبروك! تمت الموافقة عليك* 🎉\nتقدر الحين تستخدم البوت كامل\nاكتب /calc عشان تحسب تقديرك"
    else:
        user_msg = "❌ عذراً، تم رفض طلبك."

    try:
        await context.bot.send_message(info['chat_id'], user_msg, parse_mode='Markdown' if action == "موافقة" else None)
    except BadRequest:
        await context.bot.send_message(ADMIN_ID, f"⚠️ تم {action} {info['name']} بس ما قدرت أرسل له (حظر البوت)")

    await query.edit_message_text(
        f"{ '✅' if action == 'موافقة' else '❌' } تم {action}:\n{info['name']}\n@{info['username']}\nID: {user_id}"
    )

# ==================== تشغيل البوت ====================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("calc", calc_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))  # هذا السطر المهم!
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 البوت شغال كامل الحين مع حساب التقدير ونظام الموافقة!")
    app.run_polling()

if __name__ == "__main__":

    main()


