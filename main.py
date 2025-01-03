import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember, InputMediaPhoto
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
from telegram.error import Unauthorized, BadRequest
import db


# Loglarni sozlash
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# O'zingizning tokeningizni bu yerga yozing
TOKEN = '7825726998:AAFk0BYU2VtR7P7WDlLYuAoJFqcIGxf2cv4'
ADMIN_USER_ID = ['645969406','1314165390']
REQUIRED_CHANNELS = ['@quqonmanaviyhayoti','@tdtu2','@abdulaziz_abduraxmon']  # Admin tomonidan kiritiladigan majburiy kanallar

user_votes = {}
survey_text, survey_image_file_id = db.get_survey()


# Nomzodlar ro'yxatini klaviatura sifatida olish uchun yordamchi funksiya
def get_candidate_keyboard():
    candidates = db.get_candidates()
    votes = db.get_vote_count()
    keyboard = []
    for idx, candidate in candidates.items():
        vote_count = votes.get(idx, 0)
        button_text = f"{vote_count} - {candidate}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=str(idx))])
    return InlineKeyboardMarkup(keyboard)


# Foydalanuvchining kanalga a'zo ekanligini tekshirish
def check_membership(bot, user_id):
    for channel in REQUIRED_CHANNELS:
        try:
            member = bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.CREATOR]:
                return False
        except (Unauthorized, BadRequest):
            return False
    return True


# Ovozni boshlash uchun buyruq
def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id

    if not survey_text:
        update.message.reply_text("So'rovnoma matni hali kiritilmagan.")
        return

    candidates = db.get_candidates()
    if not candidates:
        update.message.reply_text("Ovoz berish uchun nomzodlar yo'q.")
        return

    if not check_membership(context.bot, user_id):
        channels_buttons = [
            [InlineKeyboardButton(channel, url=f"https://t.me/{channel[1:]}")] for channel in REQUIRED_CHANNELS
        ]
        channels_buttons.append([InlineKeyboardButton("A'zo bo'ldim ✅", callback_data="check_membership")])
        reply_markup = InlineKeyboardMarkup(channels_buttons)
        update.message.reply_text("Iltimos Ovoz berish uchun kanallarimizga a'zo bo'ling!:", reply_markup=reply_markup)
        return

    if survey_image_file_id:
        try:
            update.message.reply_photo(
                photo=survey_image_file_id,
                caption=survey_text,
                reply_markup=get_candidate_keyboard()
            )
        except BadRequest as e:
            logger.error(f"Failed to send photo: {e}")
            update.message.reply_text(
                f"{survey_text}",
                reply_markup=get_candidate_keyboard()
            )
    else:
        update.message.reply_text(
            f"{survey_text}",
            reply_markup=get_candidate_keyboard()
        )


# Tugma bosishlarini boshqarish
def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id

    if query.data == "check_membership":
        if check_membership(context.bot, user_id):
            if survey_image_file_id:
                query.message.reply_photo(
                    photo=survey_image_file_id,
                    caption=survey_text,
                    reply_markup=get_candidate_keyboard()
                )
            else:
                query.message.reply_text(
                    f"{survey_text}",
                    reply_markup=get_candidate_keyboard()
                )
        else:
            query.answer("Siz hali a'zo bo'lmadingiz. Ovoz berish uchun kanallarimizga a'zo bo'ling !.")
        return

    if query.data.startswith("edit_"):
        candidate_id = query.data.split("_")[1]
        context.user_data['edit_candidate'] = candidate_id
        query.message.reply_text("Iltimos, yangi nomzod nomini kiriting:")
        return

    if query.data.startswith("delete_"):
        candidate_id = query.data.split("_")[1]
        db.delete_candidate(candidate_id)
        query.message.reply_text("Nomzod o'chirildi.✅")
        return

    if not check_membership(context.bot, user_id):
        query.answer("Iltimos, avval kanalga a'zo bo'ling.")
        return

    if str(user_id) in user_votes:
        votes = db.get_vote_count()
        query.message.reply_text(f"Siz faqat bir marta ovoz bera olasiz.")
        query.message.reply_text("Hozirgi ovozlar:📊 ", reply_markup=get_candidate_keyboard())
        return

    candidate_id = query.data
    db.record_vote(user_id, candidate_id)
    user_votes[str(user_id)] = candidate_id

    query.message.reply_text(
        f" Siz <b> <i>{db.get_candidates()[candidate_id]}ga </i></b> ovoz berdingiz⚡️. So'rovnomada ishtirok etganingiz uchun rahmat! Rasmiy sahifalarimizni kuzatib boring.",
        parse_mode='HTML',
        reply_markup=get_candidate_keyboard())


# Nomzod qo'shish buyrug'i (faqat admin uchun)
def add_candidate(update: Update, context: CallbackContext) -> None:
    if str(update.message.from_user.id) != ADMIN_USER_ID:
        update.message.reply_text("Siz bu buyruqni ishlatishga ruxsatingiz yo'q.")
        return
    context.user_data['add_candidate'] = True
    update.message.reply_text("Iltimos, nomzodning ismini kiriting.")


def edit_candidate(update: Update, context: CallbackContext) -> None:
    if str(update.message.from_user.id) != ADMIN_USER_ID:
        update.message.reply_text("Siz bu buyruqni ishlatishga ruxsatingiz yo'q.")
        return
    candidates = db.get_candidates()
    keyboard = [[InlineKeyboardButton(candidate, callback_data=f"edit_{candidate_id}")] for candidate_id, candidate in
                candidates.items()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Tahrir qilish uchun nomzodni tanlang:", reply_markup=reply_markup)


def delete_candidate(update: Update, context: CallbackContext) -> None:
    if str(update.message.from_user.id) != ADMIN_USER_ID:
        update.message.reply_text("Siz bu buyruqni ishlatishga ruxsatingiz yo'q.")
        return
    candidates = db.get_candidates()
    keyboard = [[InlineKeyboardButton(candidate, callback_data=f"delete_{candidate_id}")] for candidate_id, candidate in
                candidates.items()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("O'chirish uchun nomzodni tanlang:", reply_markup=reply_markup)


def receive_message(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id

    if context.user_data.get('add_candidate'):
        db.add_candidate(update.message.text)
        update.message.reply_text("Nomzod qo'shildi.✅")
        del context.user_data['add_candidate']

    elif 'edit_candidate' in context.user_data:
        candidate_id = context.user_data['edit_candidate']
        db.update_candidate(candidate_id, update.message.text)
        update.message.reply_text("Nomzod tahrirlandi.✅")
        del context.user_data['edit_candidate']

    elif context.user_data.get('set_survey_text'):
        survey_text = update.message.text
        if not survey_text:  # Check if the survey text is empty
            update.message.reply_text("So'rovnoma matni bo'sh bo'lishi mumkin emas. Iltimos, to'g'ri matn kiriting.")
            return

        context.user_data['survey_text'] = survey_text
        del context.user_data['set_survey_text']
        context.user_data['set_survey_image'] = True
        update.message.reply_text("Iltimos, so'rovnoma uchun rasm yuboring (jpg yoki png formatda):")

    elif context.user_data.get('set_survey_image'):
        survey_text = context.user_data['survey_text']
        if update.message.photo:
            photo = update.message.photo[-1]  # get the highest resolution photo
            photo_file_id = photo.file_id
            db.set_survey(survey_text, photo_file_id)
            update.message.reply_text("So'rovnoma yangilandi.✅")
            del context.user_data['set_survey_image']
            del context.user_data['survey_text']

            # Yangi so'rovnoma matnini yuborish
            update.message.reply_text("Yangi so'rovnoma:")
            update.message.reply_photo(
                photo=photo_file_id,
                caption=survey_text,
                reply_markup=get_candidate_keyboard()
            )
        else:
            update.message.reply_text("To'g'ri formatda rasm yuboring (jpg yoki png).")


def set_survey(update: Update, context: CallbackContext) -> None:
    if str(update.message.from_user.id) != ADMIN_USER_ID:
        update.message.reply_text("Siz bu buyruqni ishlatishga ruxsatingiz yo'q.")
        return
    context.user_data['set_survey_text'] = True
    update.message.reply_text("Iltimos, so'rovnoma matnini kiriting:")


def main() -> None:
    updater = Updater(TOKEN)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("add_candidate", add_candidate))
    dispatcher.add_handler(CommandHandler("edit_candidate", edit_candidate))
    dispatcher.add_handler(CommandHandler("delete_candidate", delete_candidate))
    dispatcher.add_handler(CommandHandler("setsurvey", set_survey))

    dispatcher.add_handler(CallbackQueryHandler(button))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, receive_message))
    dispatcher.add_handler(MessageHandler(Filters.photo & ~Filters.command, receive_message))

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
