import logging
import asyncio
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from config import BOT_TOKEN, ADMIN_IDS, SUPPORT_USERNAME, SMS_ACTIVATE_API_KEY
from database import Database
from sms_activate import SmsActivate

sms = SmsActivate(SMS_ACTIVATE_API_KEY)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

db = Database()

# States
(WAITING_AMOUNT, WAITING_TRANSFER_PROOF, WAITING_TON_PROOF,
 ADMIN_ADD_ACCOUNT, ADMIN_SET_PRICE, ADMIN_SELECT_COUNTRY) = range(6)

# ───────────────────────────── HELPERS ─────────────────────────────

def get_user_profile(user_id):
    user = db.get_user(user_id)
    if not user:
        return None
    join_time = user.get('join_time', 'غير معروف')
    balance = user.get('balance', 0)
    username = user.get('username', 'بدون يوزر')
    return user, balance, join_time, username

def main_menu_keyboard(user_id):
    is_admin = user_id in ADMIN_IDS
    keyboard = [
        [InlineKeyboardButton("🛒 شراء حساب جديد", callback_data="buy_account")],
        [InlineKeyboardButton("💰 الأرخص", callback_data="cheapest")],
        [InlineKeyboardButton("📦 مشترياتي", callback_data="my_purchases"),
         InlineKeyboardButton("👤 معلوماتي", callback_data="my_info")],
        [InlineKeyboardButton("💵 شحن رصيد", callback_data="charge_balance"),
         InlineKeyboardButton("📜 الشروط", callback_data="terms")],
        [InlineKeyboardButton("🆘 الدعم الفني", url=f"https://t.me/{SUPPORT_USERNAME}")],
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton("⚙️ لوحة الإدارة", callback_data="admin_panel")])
    return InlineKeyboardMarkup(keyboard)

async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, text=None):
    user = update.effective_user
    db.register_user(user.id, user.username or "", user.first_name or "")
    msg = text or (
        f"📌 أنت الآن في المكان الصحيح\n"
        f"📱 أرقام مؤقتة لتفعيل حساباتك\n"
        f"💸 أسعار منافسة وجودة عالية\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💰 رصيدك الحالي: {db.get_balance(user.id):,.0f} د.ع\n"
        f"🆔 الايدي: {user.id}\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"👇 اختر الخدمة المناسبة لك 👇"
    )
    kb = main_menu_keyboard(user.id)
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=kb)
    else:
        await update.message.reply_text(msg, reply_markup=kb)

# ───────────────────────────── START ─────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_main_menu(update, context)

# ───────────────────────────── MY INFO ─────────────────────────────

async def my_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    db_user = db.get_user(user.id)
    if not db_user:
        await query.edit_message_text("❌ لم يتم العثور على بياناتك.")
        return
    purchases = db.get_user_purchases(user.id)
    text = (
        f"👤 ملفك الشخصي\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 الايدي: {user.id}\n"
        f"👤 الاسم: {db_user.get('first_name','')}\n"
        f"📛 اليوزر: @{db_user.get('username','بدون يوزر')}\n"
        f"💰 الرصيد: {db_user.get('balance',0):,.0f} د.ع\n"
        f"🕐 وقت الانضمام: {db_user.get('join_time','')}\n"
        f"🛒 عدد المشتريات: {len(purchases)}\n"
        f"━━━━━━━━━━━━━━━━━━━"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]])
    await query.edit_message_text(text, reply_markup=kb)

# ───────────────────────────── PURCHASES ─────────────────────────────

async def my_purchases(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    purchases = db.get_user_purchases(user.id)
    if not purchases:
        text = "📦 لا توجد مشتريات بعد."
    else:
        text = "📦 مشترياتك:\n━━━━━━━━━━━━━━━━━━━\n"
        for i, p in enumerate(purchases, 1):
            text += (
                f"{i}. 📱 {p['phone']}\n"
                f"   🌍 {p['country']} | 💰 {p['price']:,.0f} د.ع\n"
                f"   🕐 {p['date']}\n\n"
            )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]])
    await query.edit_message_text(text, reply_markup=kb)

# ───────────────────────────── TERMS ─────────────────────────────

async def terms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        "📜 اتفاقية الاستخدام\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "1️⃣ عدم الاسترجاع: لا نرد المبالغ بعد الشراء\n"
        "2️⃣ صلاحية الكود: يعمل لمرة واحدة فقط\n"
        "3️⃣ المسؤولية: المستخدم يتحمل كامل المسؤولية\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "✅ بالضغط على رجوع فإنك توافق على الشروط"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع (موافقة على الشروط)", callback_data="main_menu")]])
    await query.edit_message_text(text, reply_markup=kb)

# ───────────────────────────── BUY ─────────────────────────────

# ───── قائمة الدول من sms-activate مع الأعلام ─────
COUNTRY_FLAGS = {
    "روسيا": "🇷🇺",
    "أوكرانيا": "🇺🇦",
    "كازاخستان": "🇰🇿",
    "الصين": "🇨🇳",
    "الفلبين": "🇵🇭",
    "ميانمار": "🇲🇲",
    "إندونيسيا": "🇮🇩",
    "ماليزيا": "🇲🇾",
    "كينيا": "🇰🇪",
    "تنزانيا": "🇹🇿",
    "فيتنام": "🇻🇳",
    "كيرغيزستان": "🇰🇬",
    "الهند": "🇮🇳",
    "إسرائيل": "🇮🇱",
    "هونغ كونغ": "🇭🇰",
    "بولندا": "🇵🇱",
    "إنجلترا": "🇬🇧",
    "مدغشقر": "🇲🇬",
    "الكونغو": "🇨🇩",
    "نيجيريا": "🇳🇬",
    "الولايات المتحدة": "🇺🇸",
    "إندونيسيا (فيرتوال)": "🇮🇩",
    "لاوس": "🇱🇦",
    "هايتي": "🇭🇹",
    "غانا": "🇬🇭",
    "مصر": "🇪🇬",
    "كمبوديا": "🇰🇭",
    "نيبال": "🇳🇵",
    "موزمبيق": "🇲🇿",
    "غواتيمالا": "🇬🇹",
    "باكستان": "🇵🇰",
    "بنغلاديش": "🇧🇩",
    "سنغافورة": "🇸🇬",
    "أوزبكستان": "🇺🇿",
    "تركيا": "🇹🇷",
    "الإمارات": "🇦🇪",
    "السعودية": "🇸🇦",
    "العراق": "🇮🇶",
    "المغرب": "🇲🇦",
    "الجزائر": "🇩🇿",
    "ليبيا": "🇱🇾",
    "السودان": "🇸🇩",
    "إثيوبيا": "🇪🇹",
    "سريلانكا": "🇱🇰",
    "تايلاند": "🇹🇭",
    "أذربيجان": "🇦🇿",
    "طاجيكستان": "🇹🇯",
    "بيلاروسيا": "🇧🇾",
    "غينيا": "🇬🇳",
    "زيمبابوي": "🇿🇼",
    "كولومبيا": "🇨🇴",
    "البرازيل": "🇧🇷",
    "المكسيك": "🇲🇽",
    "الأرجنتين": "🇦🇷",
    "أوغندا": "🇺🇬",
    "رواندا": "🇷🇼",
    "أفريقيا الجنوبية": "🇿🇦",
    "أرمينيا": "🇦🇲",
    "جورجيا": "🇬🇪",
    "مولدوفا": "🇲🇩",
    "كرواتيا": "🇭🇷",
    "إيران": "🇮🇷",
    "اليمن": "🇾🇪",
    "سوريا": "🇸🇾",
    "الأردن": "🇯🇴",
    "لبنان": "🇱🇧",
    "تونس": "🇹🇳",
    "موريتانيا": "🇲🇷",
    "الكاميرون": "🇨🇲",
    "كوت ديفوار": "🇨🇮",
    "السنغال": "🇸🇳",
    "زامبيا": "🇿🇲",
    "ألبانيا": "🇦🇱",
    "بيرو": "🇵🇪",
    "فنزويلا": "🇻🇪",
    "الإكوادور": "🇪🇨",
    "بوليفيا": "🇧🇴",
    "باراغواي": "🇵🇾",
    "كوستاريكا": "🇨🇷",
    "هندوراس": "🇭🇳",
    "نيكاراغوا": "🇳🇮",
    "بنما": "🇵🇦",
    "جامايكا": "🇯🇲",
    "ترينيداد وتوباغو": "🇹🇹",
    "بورما": "🇲🇲",
    "تيمور الشرقية": "🇹🇱",
    "ماكاو": "🇲🇴",
    "سيراليون": "🇸🇱",
    "أنغولا": "🇦🇴",
    "بوروندي": "🇧🇮",
    "بنين": "🇧🇯",
    "غامبيا": "🇬🇲",
    "ليسوتو": "🇱🇸",
    "ملاوي": "🇲🇼",
}

def get_flag(country_name: str) -> str:
    """إرجاع علم الدولة أو 🌍 افتراضي"""
    return COUNTRY_FLAGS.get(country_name, "🌍")

async def buy_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # جلب الدول والأسعار من قاعدة البيانات
    countries = db.get_all_countries_with_prices()
    if not countries:
        await query.edit_message_text(
            "❌ لا توجد دول مضافة بعد.\nتواصل مع الأدمن.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]))
        return

    keyboard = []
    for c in countries:
        flag = get_flag(c['country'])
        keyboard.append([InlineKeyboardButton(
            f"{flag} {c['country']} | 💰{c['price']:,.0f} د.ع",
            callback_data=f"select_country_{c['country']}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")])
    await query.edit_message_text(
        "🛒 اختر الدولة:\n━━━━━━━━━━━━━━━━━━━",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def select_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    country = query.data.replace("select_country_", "")
    price = db.get_country_price(country)
    balance = db.get_balance(update.effective_user.id)
    text = (
        f"🌍 الدولة: {country}\n"
        f"💰 السعر: {price:,.0f} د.ع\n"
        f"👛 رصيدك: {balance:,.0f} د.ع\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
    )
    if balance < price:
        text += "❌ رصيدك غير كافٍ! قم بشحن رصيدك أولاً."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("💵 شحن رصيد", callback_data="charge_balance")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="buy_account")]
        ])
    else:
        text += "هل تريد الشراء؟"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ تأكيد الشراء", callback_data=f"confirm_buy_{country}")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="buy_account")]
        ])
    await query.edit_message_text(text, reply_markup=kb)

async def confirm_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("⏳ جاري شراء الرقم...")
    user = update.effective_user
    country = query.data.replace("confirm_buy_", "")
    price = db.get_country_price(country)
    balance = db.get_balance(user.id)

    if balance < price:
        await query.edit_message_text(
            "❌ رصيدك غير كافٍ! قم بشحن رصيدك أولاً.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💵 شحن رصيد", callback_data="charge_balance")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]
            ]))
        return

    # جلب كود الدولة من sms-activate
    country_code = sms.get_country_code(country)
    if country_code is None:
        await query.edit_message_text(
            f"❌ الدولة '{country}' غير مدعومة حالياً.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]))
        return

    # إرسال رسالة انتظار
    await query.edit_message_text(
        "⏳ جاري شراء الرقم من sms-activate...\nانتظر لحظة 🙏"
    )

    # شراء الرقم تلقائياً بخدمة تيليغرام
    activation_id, phone = sms.buy_number(country_code, service="tg")

    if not phone:
        await query.edit_message_text(
            f"❌ لا توجد أرقام متاحة لـ {country} الآن.\nحاول دولة أخرى أو لاحقاً.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 تجربة دولة أخرى", callback_data="buy_account")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]
            ]))
        return

    # خصم الرصيد وحفظ العملية
    db.deduct_balance(user.id, price)
    db.add_account(f"+{phone}", country, code=f"pending_{activation_id}")
    account_id = db.get_available_account(country)
    if account_id:
        db.mark_account_sold(account_id['id'], user.id)
    db.add_purchase(user.id, f"+{phone}", country, price)

    # حفظ activation_id في context للزبون
    context.user_data[f'activation_{user.id}'] = activation_id

    await query.edit_message_text(
        f"✅ تم شراء الرقم بنجاح!\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📱 الرقم: <code>+{phone}</code>\n"
        f"🌍 الدولة: {country}\n"
        f"💰 المبلغ المدفوع: {price:,.0f} د.ع\n"
        f"💰 الرصيد المتبقي: {db.get_balance(user.id):,.0f} د.ع\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📲 الخطوات:\n"
        f"1. افتح تيليغرام وسجّل بهذا الرقم\n"
        f"2. اضغط 'استلام الكود' بعد طلب الكود\n"
        f"━━━━━━━━━━━━━━━━━━━",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📩 استلام الكود", callback_data=f"recvcode_{activation_id}_{phone}")],
            [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")]
        ])
    )


async def receive_sms_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """زبون يضغط استلام الكود"""
    query = update.callback_query
    await query.answer("⏳ جاري جلب الكود...")

    parts = query.data.replace("recvcode_", "").split("_")
    activation_id = parts[0]
    phone = parts[1]

    import asyncio
    code = None
    # نحاول 3 مرات كل 5 ثواني
    for _ in range(3):
        code = sms.get_sms_code(activation_id)
        if code:
            break
        await asyncio.sleep(5)

    if not code:
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 إعادة المحاولة", callback_data=f"recvcode_{activation_id}_{phone}")],
                [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")]
            ])
        )
        await query.answer("⏳ الكود لم يصل بعد، اضغط إعادة المحاولة بعد دقيقة.", show_alert=True)
        return

    # تحديث الكود في قاعدة البيانات
    with db._connect() as conn:
        conn.execute("UPDATE accounts SET code = ? WHERE phone = ?", (code, f"+{phone}"))

    await query.edit_message_text(
        f"✅ وصل الكود!\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📱 الرقم: <code>+{phone}</code>\n"
        f"🔑 كود التفعيل: <code>{code}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ الكود يعمل لمرة واحدة فقط",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")]]))


# ───────────────────────────── CHEAPEST ─────────────────────────────

async def cheapest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    countries = db.get_countries_sorted_by_price()
    if not countries:
        text = "❌ لا توجد أرقام متاحة."
    else:
        text = "💰 الأرقام الأرخص:\n━━━━━━━━━━━━━━━━━━━\n"
        for c in countries[:10]:
            count = db.get_country_count(c['country'])
            text += f"🌍 {c['country']} | 💰 {c['price']:,.0f} د.ع | 📱 {count} رقم\n"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]])
    await query.edit_message_text(text, reply_markup=kb)

# ───────────────────────────── CHARGE BALANCE ─────────────────────────────

async def charge_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        "💵 شحن الرصيد\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "اختر طريقة الدفع:"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📲 تحويل رقم (زين كاش / آسيا)", callback_data="charge_transfer")],
        [InlineKeyboardButton("💎 TON Keeper", callback_data="charge_ton")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]
    ])
    await query.edit_message_text(text, reply_markup=kb)

async def charge_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    from config import TRANSFER_NUMBER
    text = (
        "📲 طريقة التحويل البنكي\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"📱 رقم التحويل: {TRANSFER_NUMBER}\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "📝 الخطوات:\n"
        "1. حول المبلغ على الرقم أعلاه\n"
        "2. أرسل إيصال التحويل (صورة)\n"
        "3. سيتم تفعيل رصيدك خلال دقائق\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "📤 أرسل صورة الإيصال الآن:"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="charge_balance")]])
    await query.edit_message_text(text, reply_markup=kb)
    context.user_data['awaiting_transfer_proof'] = True
    return WAITING_TRANSFER_PROOF

async def charge_ton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    from config import TON_ADDRESS
    text = (
        "💎 طريقة TON Keeper\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"👛 عنوان المحفظة:\n`{TON_ADDRESS}`\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "📝 الخطوات:\n"
        "1. افتح TON Keeper\n"
        "2. أرسل TON على العنوان أعلاه\n"
        "3. أرسل صورة الإيصال هنا\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "📤 أرسل صورة الإيصال الآن:"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="charge_balance")]])
    await query.edit_message_text(text, reply_markup=kb, parse_mode='Markdown')
    context.user_data['awaiting_ton_proof'] = True
    return WAITING_TON_PROOF

async def receive_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    method = "تحويل رقم" if context.user_data.get('awaiting_transfer_proof') else "TON Keeper"
    context.user_data['awaiting_transfer_proof'] = False
    context.user_data['awaiting_ton_proof'] = False

    # Forward to admins
    for admin_id in ADMIN_IDS:
        try:
            kb = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ قبول", callback_data=f"approve_{user.id}"),
                    InlineKeyboardButton("❌ رفض", callback_data=f"reject_{user.id}")
                ]
            ])
            caption = (
                f"💰 طلب شحن رصيد جديد\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"👤 المستخدم: {user.first_name}\n"
                f"🆔 ID: {user.id}\n"
                f"📛 يوزر: @{user.username or 'بدون'}\n"
                f"💳 الطريقة: {method}\n"
                f"━━━━━━━━━━━━━━━━━━━"
            )
            if update.message.photo:
                await context.bot.send_photo(admin_id, update.message.photo[-1].file_id,
                                             caption=caption, reply_markup=kb)
            else:
                await context.bot.send_message(admin_id, caption + "\n⚠️ لم يرسل صورة", reply_markup=kb)
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")

    await update.message.reply_text(
        "✅ تم إرسال طلبك!\n"
        "⏳ سيتم مراجعته وتفعيل رصيدك قريباً.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")]]))
    return ConversationHandler.END

# ───────────────────────────── ADMIN APPROVE/REJECT ─────────────────────────────

async def approve_charge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if update.effective_user.id not in ADMIN_IDS:
        await query.answer("❌ غير مصرح!")
        return
    await query.answer()
    target_id = int(query.data.replace("approve_", ""))
    context.user_data['approving_user'] = target_id
    await query.edit_message_caption(
        query.message.caption + "\n\n⏳ أدخل المبلغ بالدينار العراقي:"
        if query.message.caption else "⏳ أدخل المبلغ بالدينار العراقي:"
    )
    return WAITING_AMOUNT

async def reject_charge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if update.effective_user.id not in ADMIN_IDS:
        await query.answer("❌ غير مصرح!")
        return
    await query.answer()
    target_id = int(query.data.replace("reject_", ""))
    try:
        await context.bot.send_message(target_id,
            "❌ تم رفض طلب شحن رصيدك.\n"
            "للاستفسار تواصل مع الدعم الفني.")
    except:
        pass
    await query.edit_message_reply_markup(None)
    await query.message.reply_text("✅ تم رفض الطلب.")

async def receive_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    try:
        amount = float(update.message.text.replace(",", ""))
    except:
        await update.message.reply_text("❌ أدخل رقماً صحيحاً.")
        return WAITING_AMOUNT
    target_id = context.user_data.get('approving_user')
    if not target_id:
        return ConversationHandler.END
    db.add_balance(target_id, amount)
    new_bal = db.get_balance(target_id)
    await update.message.reply_text(f"✅ تم إضافة {amount:,.0f} د.ع للمستخدم {target_id}")
    try:
        await context.bot.send_message(target_id,
            f"✅ تم شحن رصيدك!\n"
            f"💰 المبلغ المضاف: {amount:,.0f} د.ع\n"
            f"💼 رصيدك الحالي: {new_bal:,.0f} د.ع")
    except:
        pass
    return ConversationHandler.END

# ───────────────────────────── ADMIN PANEL ─────────────────────────────

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if update.effective_user.id not in ADMIN_IDS:
        await query.answer("❌ غير مصرح!")
        return
    await query.answer()
    stats = db.get_stats()
    text = (
        f"⚙️ لوحة الإدارة\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👥 المستخدمون: {stats['users']}\n"
        f"📱 الأرقام المتاحة: {stats['available']}\n"
        f"✅ الأرقام المباعة: {stats['sold']}\n"
        f"💰 إجمالي المبيعات: {stats['revenue']:,.0f} د.ع\n"
        f"━━━━━━━━━━━━━━━━━━━"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ إضافة أرقام", callback_data="admin_add_accounts")],
        [InlineKeyboardButton("🤖 جلب تلقائي من sms-activate", callback_data="admin_auto_fetch")],
        [InlineKeyboardButton("🌍 إدارة الدول والأسعار", callback_data="admin_manage_countries")],
        [InlineKeyboardButton("👥 المستخدمون", callback_data="admin_users")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]
    ])
    await query.edit_message_text(text, reply_markup=kb)

async def admin_add_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if update.effective_user.id not in ADMIN_IDS:
        await query.answer("❌ غير مصرح!")
        return
    await query.answer()
    countries = db.get_available_countries()
    keyboard = []
    for c in countries:
        flag = get_flag(c['country'])
        keyboard.append([InlineKeyboardButton(
            f"{flag} {c['country']} | {c['price']:,.0f} د.ع",
            callback_data=f"admin_add_to_{c['country']}"
        )])
    keyboard.append([InlineKeyboardButton("➕ دولة جديدة", callback_data="admin_new_country")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")])
    await query.edit_message_text(
        "➕ إضافة أرقام - اختر الدولة:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_new_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if update.effective_user.id not in ADMIN_IDS:
        await query.answer("❌ غير مصرح!")
        return
    await query.answer()
    await query.edit_message_text(
        "🌍 أدخل اسم الدولة:\n(مثال: العراق، السعودية، مصر)"
    )
    context.user_data['admin_state'] = 'new_country'
    return ADMIN_SELECT_COUNTRY

async def admin_add_to_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if update.effective_user.id not in ADMIN_IDS:
        await query.answer("❌ غير مصرح!")
        return
    await query.answer()
    country = query.data.replace("admin_add_to_", "")
    context.user_data['selected_country'] = country
    await query.edit_message_text(
        f"📱 إضافة أرقام للدولة: {country}\n\n"
        "أرسل الأرقام (كل رقم في سطر):\n\n"
        "📌 بدون كود:\n+9647701234567\n\n"
        "📌 مع كود التفعيل:\n+9647701234567:12345\n+9647801234567:67890"
    )
    context.user_data['admin_state'] = 'adding_accounts'
    return ADMIN_ADD_ACCOUNT

async def admin_receive_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    state = context.user_data.get('admin_state')

    if state == 'new_country':
        country = update.message.text.strip()
        context.user_data['selected_country'] = country
        context.user_data['admin_state'] = 'setting_price'
        await update.message.reply_text(
            f"💰 أدخل سعر الرقم بالدينار العراقي للدولة: {country}"
        )
        return ADMIN_SET_PRICE

    elif state == 'adding_accounts':
        country = context.user_data.get('selected_country')
        phones = [p.strip() for p in update.message.text.strip().split('\n') if p.strip()]
        added = 0
        for line in phones:
            if ':' in line:
                phone, code = line.split(':', 1)
                phone = phone.strip()
                code = code.strip()
            else:
                phone = line.strip()
                code = None
            if db.add_account(phone, country, code=code):
                added += 1
        await update.message.reply_text(
            f"✅ تم إضافة {added} رقم للدولة {country}!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لوحة الإدارة", callback_data="admin_panel")]]))
        return ConversationHandler.END

    return ConversationHandler.END

async def admin_receive_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    try:
        price = float(update.message.text.replace(",", ""))
    except:
        await update.message.reply_text("❌ أدخل رقماً صحيحاً للسعر.")
        return ADMIN_SET_PRICE
    country = context.user_data.get('selected_country')
    db.set_country_price(country, price)
    context.user_data['admin_state'] = 'adding_accounts'
    await update.message.reply_text(
        f"✅ تم تعيين السعر {price:,.0f} د.ع للدولة {country}\n\n"
        "الآن أرسل الأرقام (كل رقم في سطر):"
    )
    return ADMIN_ADD_ACCOUNT

async def admin_manage_countries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if update.effective_user.id not in ADMIN_IDS:
        await query.answer("❌ غير مصرح!")
        return
    await query.answer()
    countries = db.get_available_countries()
    if not countries:
        text = "❌ لا توجد دول."
    else:
        text = "🌍 الدول والأسعار:\n━━━━━━━━━━━━━━━━━━━\n"
        for c in countries:
            count = db.get_country_count(c['country'])
            text += f"🌍 {c['country']} | {c['price']:,.0f} د.ع | {count} رقم\n"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]])
    await query.edit_message_text(text, reply_markup=kb)

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if update.effective_user.id not in ADMIN_IDS:
        await query.answer("❌ غير مصرح!")
        return
    await query.answer()
    users = db.get_all_users()
    text = f"👥 المستخدمون ({len(users)}):\n━━━━━━━━━━━━━━━━━━━\n"
    for u in users[:20]:
        text += f"🆔 {u['user_id']} | @{u.get('username','?')} | 💰 {u.get('balance',0):,.0f} د.ع\n"
    if len(users) > 20:
        text += f"\n... و{len(users)-20} آخرين"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]])
    await query.edit_message_text(text, reply_markup=kb)

# ───────────────────────────── MAIN MENU CALLBACK ─────────────────────────────

async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_main_menu(update, context)

# ───────────────────────────── AUTO FETCH FROM SMS-ACTIVATE ─────────────────────────────

async def admin_auto_fetch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة الدول للجلب التلقائي"""
    query = update.callback_query
    if update.effective_user.id not in ADMIN_IDS:
        await query.answer("❌ غير مصرح!")
        return
    await query.answer()

    # جلب رصيد sms-activate
    balance = sms.get_balance()
    balance_text = f"💰 رصيدك في sms-activate: {balance:.2f}$" if balance is not None else "⚠️ تعذر جلب الرصيد"

    # عرض الدول المتاحة في قاعدة البيانات
    countries = db.get_available_countries()
    keyboard = []
    for c in countries:
        country_code = sms.get_country_code(c['country'])
        if country_code is not None:
            keyboard.append([InlineKeyboardButton(
                f"🤖 {c['country']}",
                callback_data=f"autofetch_{c['country']}"
            )])

    if not keyboard:
        await query.edit_message_text(
            f"{balance_text}\n\n❌ لا توجد دول مضافة في قاعدة البيانات.\nأضف دولة أولاً من ➕ إضافة أرقام",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]]))
        return

    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")])
    await query.edit_message_text(
        f"{balance_text}\n\n🤖 اختر الدولة للجلب التلقائي:\n(سيشتري رقم واحد من sms-activate)",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def admin_do_autofetch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنفيذ الجلب التلقائي للرقم"""
    query = update.callback_query
    if update.effective_user.id not in ADMIN_IDS:
        await query.answer("❌ غير مصرح!")
        return
    await query.answer("⏳ جاري الشراء...")

    country = query.data.replace("autofetch_", "")
    country_code = sms.get_country_code(country)

    if country_code is None:
        await query.edit_message_text(
            f"❌ الدولة '{country}' غير مدعومة في sms-activate.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="admin_auto_fetch")]]))
        return

    activation_id, phone = sms.buy_number(country_code, service="any")

    if not phone:
        await query.edit_message_text(
            f"❌ لا توجد أرقام متاحة لـ {country} الآن.\nحاول دولة أخرى أو لاحقاً.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="admin_auto_fetch")]]))
        return

    # حفظ الرقم مع activation_id كـ code مؤقتاً
    db.add_account(f"+{phone}", country, code=f"انتظار_كود_{activation_id}")

    await query.edit_message_text(
        f"✅ تم شراء الرقم بنجاح!\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📱 الرقم: +{phone}\n"
        f"🌍 الدولة: {country}\n"
        f"🆔 ID التفعيل: {activation_id}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"⏳ الكود سيصل خلال دقائق.\n"
        f"اضغط 'جلب الكود' بعد إرسال الرقم للتطبيق.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📩 جلب الكود الآن", callback_data=f"getcode_{activation_id}_{phone}_{country}")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_auto_fetch")]
        ])
    )


async def admin_get_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """جلب كود SMS من sms-activate"""
    query = update.callback_query
    if update.effective_user.id not in ADMIN_IDS:
        await query.answer("❌ غير مصرح!")
        return
    await query.answer("⏳ جاري جلب الكود...")

    parts = query.data.replace("getcode_", "").split("_")
    activation_id = parts[0]
    phone = parts[1]
    country = "_".join(parts[2:])

    code = sms.get_sms_code(activation_id)

    if not code:
        await query.edit_message_text(
            f"⏳ الكود لم يصل بعد.\n"
            f"📱 الرقم: +{phone}\n"
            f"انتظر دقيقة واضغط مرة ثانية.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 تحديث", callback_data=f"getcode_{activation_id}_{phone}_{country}")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="admin_auto_fetch")]
            ])
        )
        return

    # تحديث الكود في قاعدة البيانات
    with db._connect() as conn:
        conn.execute("UPDATE accounts SET code = ? WHERE phone = ?", (code, f"+{phone}"))

    await query.edit_message_text(
        f"✅ تم استلام الكود!\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📱 الرقم: +{phone}\n"
        f"🔑 الكود: {code}\n"
        f"🌍 الدولة: {country}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"✅ تم حفظ الرقم والكود في قاعدة البيانات!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🤖 جلب رقم آخر", callback_data="admin_auto_fetch")],
            [InlineKeyboardButton("🔙 لوحة الإدارة", callback_data="admin_panel")]
        ])
    )


# ───────────────────────────── MAIN ─────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    charge_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(charge_transfer, pattern="^charge_transfer$"),
            CallbackQueryHandler(charge_ton, pattern="^charge_ton$"),
        ],
        states={
            WAITING_TRANSFER_PROOF: [MessageHandler(filters.PHOTO | filters.TEXT, receive_proof)],
            WAITING_TON_PROOF: [MessageHandler(filters.PHOTO | filters.TEXT, receive_proof)],
            WAITING_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_amount)],
        },
        fallbacks=[CommandHandler("start", start)],
        per_message=False
    )

    admin_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_new_country, pattern="^admin_new_country$"),
            CallbackQueryHandler(admin_add_to_country, pattern="^admin_add_to_"),
        ],
        states={
            ADMIN_SELECT_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_receive_accounts)],
            ADMIN_SET_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_receive_price)],
            ADMIN_ADD_ACCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_receive_accounts)],
        },
        fallbacks=[CommandHandler("start", start)],
        per_message=False
    )

    approve_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(approve_charge, pattern="^approve_")],
        states={
            WAITING_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_amount)],
        },
        fallbacks=[CommandHandler("start", start)],
        per_message=False
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(charge_conv)
    app.add_handler(admin_conv)
    app.add_handler(approve_conv)
    app.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(my_info, pattern="^my_info$"))
    app.add_handler(CallbackQueryHandler(my_purchases, pattern="^my_purchases$"))
    app.add_handler(CallbackQueryHandler(terms, pattern="^terms$"))
    app.add_handler(CallbackQueryHandler(buy_account, pattern="^buy_account$"))
    app.add_handler(CallbackQueryHandler(cheapest, pattern="^cheapest$"))
    app.add_handler(CallbackQueryHandler(charge_balance, pattern="^charge_balance$"))
    app.add_handler(CallbackQueryHandler(select_country, pattern="^select_country_"))
    app.add_handler(CallbackQueryHandler(confirm_buy, pattern="^confirm_buy_"))
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(admin_add_accounts, pattern="^admin_add_accounts$"))
    app.add_handler(CallbackQueryHandler(admin_manage_countries, pattern="^admin_manage_countries$"))
    app.add_handler(CallbackQueryHandler(admin_users, pattern="^admin_users$"))
    app.add_handler(CallbackQueryHandler(reject_charge, pattern="^reject_"))
    app.add_handler(CallbackQueryHandler(admin_auto_fetch, pattern="^admin_auto_fetch$"))
    app.add_handler(CallbackQueryHandler(admin_do_autofetch, pattern="^autofetch_"))
    app.add_handler(CallbackQueryHandler(admin_get_code, pattern="^getcode_"))
    app.add_handler(CallbackQueryHandler(receive_sms_code, pattern="^recvcode_"))

    print("✅ البوت يعمل...")
    app.run_polling()

if __name__ == "__main__":
    main()
