from telegram import Update
from google.cloud import firestore
from google.cloud import translate_v2 as translate
from telegram.ext import MessageHandler, filters
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from vars import TELEGRAM_TOKEN, TELEGRAM_BOT, GOOGLE_API_KEY

# Use the API key for your project
translate_client = translate.Client(GOOGLE_API_KEY)
db = firestore.Client(TELEGRAM_BOT)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="I'm a bot that can automatically translate messages in group chats. "
             "Please use the '/setlang' command to set your preferred language."
    )

async def setlang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id =  update.effective_user.id
    user_name =  update.effective_user.full_name
    if len(context.args) > 0:
        lang = context.args[0]
        print(f"saving language {lang} for user {user_id} in chat {chat_id}")
        doc_ref = db.collection(u'chats').document(str(chat_id)).collection(u'members').document(str(user_id))
        doc_ref.set({
            u'preferred_language': lang
        })
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Preferred language for {user_name} is now set to {lang}")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Please provide your two letter language code as parameter to the command, eg. /setlang en")

def get_user_lang(chat_id, user_id):
    doc_ref = db.collection(u'chats').document(str(chat_id)).collection(u'members').document(str(user_id))
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()['preferred_language']
    else:
        return None

async def translate_message(update, context):
    chat_id = update.effective_chat.id
    message_text = update.effective_message.text
    # Use the Google Translate API to translate the message into each language
    # Get the preferred languages for all members of the chat
    members_ref = db.collection(u'chats').document(str(chat_id)).collection(u'members')
    members = members_ref.stream()
    # Create a dictionary to store the translated message for each language
    translations = {}
    for doc in members:
        lang = doc.to_dict()['preferred_language']
        result = translate_client.translate(message_text, target_language=lang)
        translations[lang] = result['translatedText']

    # Send the translated message to each member of the chat
    sent_langs = []
    for lang in translations:
        members = members_ref.stream()
        for doc in members:
            if doc.to_dict()['preferred_language'] == lang and lang not in sent_langs:
                user_id = doc.id
                print(f"sending message in {lang} to {user_id} in chat {chat_id}")
                await context.bot.send_message(chat_id=chat_id, text=translations[lang], reply_to_message_id = update.effective_message.id)
                sent_langs.append(lang)




app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

start_handler = CommandHandler('start', start)
setlang_handler = CommandHandler('setlang', setlang)
message_handler = MessageHandler(filters.TEXT, translate_message)
app.add_handler(start_handler)
app.add_handler(setlang_handler)
app.add_handler(message_handler)

app.run_polling()
