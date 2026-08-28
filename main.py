import asyncio
import random
import logging
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.enums import ChatAction
import google.generativeai as genai
from config import API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY, GROUP_LINK

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Gemini Setup
genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = (
    f"Aap Telegram par ek real human ki tarah baat kar rahe hain. "
    f"Hinglish me casual, friendly aur short reply dein (1-2 lines). "
    f"Jab koi group/channel link maange tabhi yeh dein: {GROUP_LINK}"
)

def get_model():
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'flash' in m.name:
                    return genai.GenerativeModel(m.name, system_instruction=SYSTEM_PROMPT)
        return genai.GenerativeModel('gemini-1.5-flash', system_instruction=SYSTEM_PROMPT)
    except Exception:
        return genai.GenerativeModel('gemini-1.5-flash', system_instruction=SYSTEM_PROMPT)

model = get_model()

app = Client(
    "group_human_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

@app.on_message(filters.text & ~filters.me)
async def auto_reply(client: Client, message: Message):
    sender = message.from_user.first_name if message.from_user else "User"
    user_text = message.text
    chat_id = message.chat.id

    logging.info(f"📩 Naya Message Aaya [{sender}]: {user_text}")

    try:
        await client.send_chat_action(chat_id, ChatAction.TYPING)
        await asyncio.sleep(random.uniform(1.0, 2.0))

        prompt = f"User ({sender}): {user_text}\nReply:"
        response = await asyncio.to_thread(model.generate_content, prompt)
        reply_text = response.text.strip() if (response and response.text) else "Haan bhai, bolo!"

        await message.reply_text(text=reply_text, quote=True, disable_web_page_preview=True)
        logging.info(f"✅ Sent Reply: {reply_text}")

    except Exception as e:
        logging.error(f"❌ Error in reply: {e}")

async def main():
    await app.start()
    logging.info("⏳ Sabhi Groups & Channels ka peer cache load ho raha hai...")
    try:
        async for _ in app.get_dialogs():
            pass
        logging.info("✅ Saara peer cache load ho gaya!")
    except Exception as e:
        logging.warning(f"Cache load warning: {e}")

    logging.info("🚀 AI Bot ab puri tarah ready hai aur live listen kar raha hai!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
