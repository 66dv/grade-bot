from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import BadRequest
import os

# ==================== إعدادات ====================
TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
CHANNEL_USERNAME = '@CDF991' # قناتك
DEVELOPER_USERNAME = '@cdf99' # معرفك

if not TOKEN or not ADMIN_ID:
 print("خطأ: تأكد من إضافة BOT_TOKEN و ADMIN_ID في Environment Variables!")
 exit(1)

pending_users = {}
approved_users = set()
banned_users = set() # جديد: المحظورين
user_data = {}

print("🚀 البوت شغال مع إجبار الانضمام للقناة وحظر!")

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
        return False  # محاذي صح الحين



# ==================== /start ====================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
 user = update.effective_user
 user_id = user.id
 chat_id = update.effective_chat.id

 # الرسالة الترحيبية الأولى دائمًا
 welcome_msg = (
 "أهلا بك في بوت حساب التقييم 🎓\n\n"
 "إذا كان هنالك خطأ في عمل البوت، يمكنك التواصل مع المطور من خلال المعرف التالي: @cdf99"
 )
 await update.message.reply_text(welcome_msg)

 if user_id == ADMIN_ID:
 approved_users.add(ADMIN_ID)
 await update.message.reply_text("👑 يا هلا يا صاحب البوت! البوت شغال 100% 🚀")
 return

 if user_id in banned_users:
 await update.message.reply_text("🚫 أنت محظور من استخدام البوت. تواصل مع @cdf99")
 return

 # تحقق الانضمام للقناة
 if not await check_membership(context, user_id):
 keyboard = [[InlineKeyboardButton("انضم إلى قناة المطور", url=f"https://t.me/CDF991")]]
 reply_markup = InlineKeyboardMarkup(keyboard)
 await update.message.reply_text(
 "⚠️ لاستخدام البوت، يجب عليك الانضمام أولاً إلى قناة المطور:\n@CDF991",
 reply_markup=reply_markup
 )
 return

 if is_approved(user_id):
 await update.message.reply_text("🎓 مرحباً مرة ثانية! اكتب /calc لحساب تقديرك 📚")
 return

 # مستخدم جديد ومنضم → إرسال طلب موافقة
 if user_id not in pending_users:
 pending_users[user_id] = {'name': user.full_name, 'username': user.username or "لا يوجد", 'chat_id': chat_id}

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
 print("خطأ في إرسال الإشعار للأدمن")

 await update.message.reply_text("⏳ تم إرسال طلبك للموافقة، انتظر الرد قريبًا 🕐")

# ==================== /calc و handle_message (مع تحقق الانضمام) ====================
async def calc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
 user_id = update.effective_user.id
 if not is_approved(user_id):
 await update.message.reply_text("🚫 لازم تكون موافق عليك أولاً")
 return

 if not await check_membership(context, user_id):
 keyboard = [[InlineKeyboardButton("انضم إلى القناة", url=f"https://t.me/CDF991")]]
 reply_markup = InlineKeyboardMarkup(keyboard)
 await update.message.reply_text(
 "🚫 غادرت القناة! انضم مرة أخرى لاستخدام البوت @CDF991",
 reply_markup=reply_markup
 )
 return

 user_data[user_id] = {'step': 'num_courses', 'current': 1, 'grades': [], 'total': 0.0, 'num_courses': 0}
 await update.message.reply_text("📚 *كم عدد المواد؟*\nأدخل رقم فقط:", parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
 user_id = update.effective_user.id
 if not is_approved(user_id):
 return

 if not await check_membership(context, user_id):
 keyboard = [[InlineKeyboardButton("انضم إلى القناة", url=f"https://t.me/CDF991")]]
 reply_markup = InlineKeyboardMarkup(keyboard)
 await update.message.reply_text(
 "🚫 غادرت القناة! انضم مرة أخرى للاستمرار @CDF991",
 reply_markup=reply_markup
 )
 return

 text = update.message.text.strip()
 # ... باقي كود الحساب زي ما هو (ما غيرته، يشتغل عادي)

# ==================== معالجة الأزرار (مع حظر ورفع حظر) ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
 query = update.callback_query
 await query.answer()

 data = query.data
 action, user_id_str = data.split("_", 1)
 user_id = int(user_id_str)

 info = pending_users.get(user_id)

 if action == "approve":
 approved_users.add(user_id)
 pending_users.pop(user_id, None)
 msg = "✅ تمت الموافقة عليك! اكتب /calc"
 elif action == "reject":
 pending_users.pop(user_id, None)
 msg = "❌ تم رفض طلبك"
 elif action == "ban":
 banned_users.add(user_id)
 approved_users.discard(user_id)
 pending_users.pop(user_id, None)
 msg = "🚫 تم حظرك من البوت. تواصل مع @cdf99"

 if info:
 try:
 await context.bot.send_message(info['chat_id'], msg)
 except:
 pass

 await query.edit_message_text(f"{action.upper()} تم للمستخدم {user_id}")

# ==================== main ====================
def main():
 app = Application.builder().token(TOKEN).build()
 app.add_handler(CommandHandler("start", start_command))
 app.add_handler(CommandHandler("calc", calc_command))
 app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
 app.add_handler(CallbackQueryHandler(button_handler))
 app.run_polling()

if __name__ == "__main__":
 main()

