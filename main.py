import asyncio
import random
import logging
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from pyrogram.raw.functions.messages import GetAllStickers
import google.generativeai as genai
from config import API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY, GROUP_LINK

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 1. Gemini AI Setup
genai.configure(api_key=GEMINI_API_KEY)

def connect_best_model():
    priority_models = [
        "gemini-3.6-flash",
        "gemini-3.7-flash",
        "gemini-3.5-flash",
        "gemini-flash-latest",
        "gemini-1.5-flash"
    ]
    try:
        all_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for target in priority_models:
            for full_name in all_models:
                if target in full_name:
                    try:
                        m = genai.GenerativeModel(full_name)
                        m.generate_content("hi")
                        logging.info(f"🎯 AI Model Connected: {full_name}")
                        return m
                    except Exception:
                        continue
    except Exception as e:
        logging.error(f"Model selection error: {e}")
    return genai.GenerativeModel("gemini-3.6-flash")

active_ai = connect_best_model()

# 2. 100% Dynamic AI Hinglish Generator
def get_ai_reply(user_text: str, sender_name: str) -> str:
    prompt = f"""You are a young, cool Indian guy chatting with a friend on Telegram. Reply like an authentic real human in natural casual Hinglish (Hindi written in English alphabet).

Strict Guidelines:
1. Always reply in everyday casual conversational Hinglish (short & snappy).
2. Understand chat slang & questions:
   - "gf h teri" -> funny casual reply (e.g. 'nahi bhai single hu, tu setting kara de!')
   - "kidar gya" -> casual reply (e.g. 'yahi hu bhai, pani peene gaya tha. bol!')
   - "kkrh" -> 'kuch nahi bhai bas chill kar raha hu'
3. Keep it to 1-2 short sentences max.
4. NEVER say you are an AI or bot.
5. If the user asks for group/channel/link, share: {GROUP_LINK}

Friend ({sender_name}) says: "{user_text}"
Your Hinglish reply:"""

    try:
        response = active_ai.generate_content(prompt)
        if response and response.text:
            return response.text.strip()
    except Exception as e:
        logging.error(f"AI response error: {e}")
    return ""

# 3. Pyrogram Client & Auto Account Sticker Sync
app = Client(
    "group_human_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

STICKER_CACHE = []

async def load_all_stickers():
    global STICKER_CACHE
    try:
        # User account me installed saare stickers automatically load karega
        result = await app.invoke(GetAllStickers(hash=0))
        for sticker_set in result.sets:
            try:
                st_set = await app.get_sticker_set(sticker_set.short_name)
                for s in st_set.stickers:
                    STICKER_CACHE.append(s.file_id)
            except Exception:
                continue
    except Exception as e:
        logging.warning(f"Account stickers load warning: {e}")

    # Agar account me koi sticker na ho toh popular sets se load karega
    if not STICKER_CACHE:
        fallback_packs = ["HotCherry", "AnimatedDog", "Animals", "TgEmojis", "SberKot"]
        for pack in fallback_packs:
            try:
                st_set = await app.get_sticker_set(pack)
                for s in st_set.stickers:
                    STICKER_CACHE.append(s.file_id)
            except Exception:
                continue

    logging.info(f"🎨 Total {len(STICKER_CACHE)} Stickers ready in Cache!")

# Text Messages Handler
@app.on_message(filters.text & ~filters.me & ~filters.bot)
async def on_text_message(client: Client, message: Message):
    sender = message.from_user.first_name if message.from_user else "Dost"
    user_text = message.text
    chat_id = message.chat.id

    logging.info(f"📩 Naya Text [{sender}]: {user_text}")

    try:
        try:
            await client.read_chat_history(chat_id)
            await client.send_chat_action(chat_id, ChatAction.TYPING)
        except Exception:
            pass

        await asyncio.sleep(random.uniform(1.2, 2.0))

        # 8-second safety timeout on AI call
        reply = await asyncio.wait_for(
            asyncio.to_thread(get_ai_reply, user_text, sender),
            timeout=8.0
        )

        if reply:
            await message.reply_text(text=reply, quote=True, disable_web_page_preview=True)
            logging.info(f"✅ AI Replied to [{sender}]: {reply}")

    except Exception as e:
        logging.error(f"Text error: {e}")

# Sticker Messages Handler (100% Guaranteed Sticker Reply)
@app.on_message(filters.sticker & ~filters.me & ~filters.bot)
async def on_sticker_message(client: Client, message: Message):
    sender = message.from_user.first_name if message.from_user else "Dost"
    chat_id = message.chat.id

    # Auto-learn received sticker into cache
    if message.sticker and message.sticker.file_id:
        STICKER_CACHE.append(message.sticker.file_id)

    logging.info(f"🎨 Sticker received from [{sender}]")

    try:
        try:
            await client.read_chat_history(chat_id)
            await client.send_chat_action(chat_id, ChatAction.CHOOSE_STICKER)
        except Exception:
            pass

        await asyncio.sleep(random.uniform(1.0, 1.8))

        if STICKER_CACHE:
            random_sticker = random.choice(STICKER_CACHE)
            await message.reply_sticker(sticker=random_sticker, quote=True)
            logging.info(f"✅ Sent Sticker Reply to [{sender}]")
        else:
            await message.reply_sticker(sticker=message.sticker.file_id, quote=True)

    except Exception as e:
        logging.error(f"Sticker handler error: {e}")

async def main():
    await app.start()
    logging.info("⏳ Dialogs cache load ho raha hai...")
    try:
        async for _ in app.get_dialogs(limit=25):
            pass
    except Exception:
        pass

    await load_all_stickers()
    logging.info("🚀 AI Human Bot is LIVE & Ready for 24/7 Chats + Stickers!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
