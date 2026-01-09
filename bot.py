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

print("🚀 البوت شغال مع لوحة تحكم دائمة وأزرار حظر!")

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
        await update.message.reply_text("👑 يا هلا يا صاحب البوت! اكتب /panel للوحة التحكم")
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

    all_users = approved_users.union(banned_users)
    if not all_users:
        await update.message.reply_text("لا يوجد مستخدمين موافق عليهم أو محظورين حاليًا")
        return

    keyboard = []
    for uid in all_users:
        status = "🚫 محظور" if uid in banned_users else "✅ موافق"
        ban_button_text = "✅ رفع الحظر" if uid in banned_users else "🚫 حظر"
        keyboard.append([
            InlineKeyboardButton(f"{status} - ID: {uid}", callback_data=f"info_{uid}"),
            InlineKeyboardButton(ban_button_text, callback_data=f"toggle_ban_{uid}")
        ])

    keyboard.append([InlineKeyboardButton("🔄 تحديث اللوحة", callback_data="refresh_panel")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("🔧 *لوحة التحكم في المستخدمين*\nاختر مستخدم لحظره أو رفع الحظر:", parse_mode='Markdown', reply_markup=reply_markup)

# ==================== /calc ====================
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
    await update.message.reply_text("📚 *كم عدد المواد هذا الفصل؟*\n\nأدخل رقم فقط (مثال: 6)", parse_mode='Markdown')

# ==================== معالجة الرسائل النصية (الحساب) ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_approved(user_id):
        return

    if not await check_membership(context, user_id):
        keyboard = [[InlineKeyboardButton("انضم إلى القناة", url="https://t.me/CDF991")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🚫 غادرت القناة! انضم مرة أخرى للاستمرار @CDF991", reply_markup=reply_markup)
        return

    text = update.message.text.strip()
    if user_id not in user_data:
        await update.message.reply_text("⚠️ ابدأ من جديد بـ /calc")
        return

    state = user_data[user_id]

    if state['step'] == 'num_courses':
        if text.isdigit() and int(text) > 0:
            state['num_courses'] = int(text)
            state['step'] = 'enter_grade'
            await update.message.reply_text(f"📖 *المادة 1 من {state['num_courses']}*\n\nأدخل الدرجة (0-100):", parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ أدخل رقم صحيح أكبر من 0")

    elif state['step'] == 'enter_grade':
        try:
            grade = float(text)
            if 0 <= grade <= 100:
                state['grades'].append(grade)
                state['total'] += grade

                if state['current'] >= state['num_courses']:
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
                    del user_data[user_id]
                else:
                    state['current'] += 1
                    await update.message.reply_text(f"✅ تم حفظ درجة المادة {state['current']-1}")
                    await update.message.reply_text(f"📖 *المادة {state['current']} من {state['num_courses']}*\nأدخل الدرجة:", parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ الدرجة لازم تكون بين 0 و 100")
        except ValueError:
            await update.message.reply_text("❌ أدخل رقم صحيح مثل: 85 أو 92.5")

# ==================== معالجة الأزرار (كامل وشغال 100%) ====================
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
            status = "رفع الحظر عن"
        else:
            banned_users.add(target_id)
            approved_users.discard(target_id)
            status = "حظر"

        await query.edit_message_text(f"✅ تم {status} المستخدم {target_id} بنجاح!")
        await panel_command(update, context)  # تحديث اللوحة فورًا
        return

    # معالجة الطلبات الجديدة (approve/reject/ban)
    if data.startswith("approve_") or data.startswith("reject_") or data.startswith("ban_"):
        action = data.split("_")[0]
        user_id = int(data.split("_")[1])

        info = pending_users.pop(user_id, None)

        if action == "approve":
            approved_users.add(user_id)
            user_msg = "✅ *مبروك! تمت الموافقة عليك* 🎉\nتقدر الحين تستخدم البوت كامل\nاكتب /calc"
        elif action == "reject":
            user_msg = "❌ عذراً، تم رفض طلبك."
        elif action == "ban":
            banned_users.add(user_id)
            user_msg = "🚫 تم حظرك من استخدام البوت. تواصل مع @cdf99"

        if info:
            try:
                await context.bot.send_message(info['chat_id'], user_msg, parse_mode='Markdown' if action == "approve" else None)
            except BadRequest:
                await context.bot.send_message(ADMIN_ID, f"⚠️ تم {action} {info['name']} بس ما قدرت أرسل له")

        await query.edit_message_text(f"تم {action} الطلب لـ {info['name'] if info else user_id}")

# ==================== main ====================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("calc", calc_command))
    app.add_handler(CommandHandler("panel", panel_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 البوت جاهز كامل مع أزرار حظر دائمة!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
