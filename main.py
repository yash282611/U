import asyncio
import random
import logging
import json
import urllib.request
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from config import API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY, GROUP_LINK

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Smart AI Response Generator
def get_ai_reply(user_text: str, sender_name: str) -> str:
    prompt = (
        f"You are a real Indian person chatting with a friend on Telegram. "
        f"Reply in natural, cool, everyday Hinglish (Hindi written in English alphabets). "
        f"Rules:\n"
        f"1. Understand chat short-forms (kkrh = kya kar raha hai, kaisa h = kaisa hai, mast = good, wrud = what are you doing).\n"
        f"2. Keep replies short, casual, and human (1-2 lines max).\n"
        f"3. Never say you are an AI or bot. Speak like a real buddy.\n"
        f"4. If asked for link, channel, or group, share this: {GROUP_LINK}\n\n"
        f"Friend ({sender_name}) says: \"{user_text}\"\n"
        f"Your Hinglish Reply:"
    )

    # Models to try sequentially
    models = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]
    
    for model_name in models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.85, "maxOutputTokens": 100}
            }
            req = urllib.request.Request(
                url, 
                data=json.dumps(payload).encode('utf-8'), 
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                reply = res_data['candidates'][0]['content']['parts'][0]['text'].strip()
                if reply:
                    return reply
        except Exception as e:
            logging.warning(f"Model {model_name} error: {e}")
            continue

    # Human-like intelligent fallbacks
    fallbacks = [
        "Kuch nahi bhai, bas aese hi baitha tha. Tu bata?",
        "Mast hu bhai, tu suna kya chal raha hai?",
        "Haan bhai bol, sun raha hu.",
        "Bas phone chala raha tha yaar, tu bata kaisa hai?"
    ]
    return random.choice(fallbacks)

app = Client(
    "group_human_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

@app.on_message(filters.text & ~filters.me & ~filters.bot)
async def auto_reply(client: Client, message: Message):
    try:
        sender = message.from_user.first_name if message.from_user else "Dost"
        user_text = message.text
        chat_id = message.chat.id

        logging.info(f"📩 Naya Message [{sender}]: {user_text}")

        # Seen / Read status
        try:
            await client.read_chat_history(chat_id)
            await client.send_chat_action(chat_id, ChatAction.TYPING)
        except Exception:
            pass

        # Realistic human delay
        await asyncio.sleep(random.uniform(1.2, 2.5))

        # Get dynamic AI response
        reply_text = await asyncio.to_thread(get_ai_reply, user_text, sender)

        # Send Reply
        await message.reply_text(text=reply_text, quote=True, disable_web_page_preview=True)
        logging.info(f"✅ Replied to [{sender}]: {reply_text}")

    except Exception as e:
        logging.error(f"Error in handler: {e}")

async def main():
    await app.start()
    logging.info("⏳ Dialogs sync ho rahe hain...")
    try:
        async for _ in app.get_dialogs(limit=50):
            pass
    except Exception:
        pass
    logging.info("🚀 AI Human Bot is LIVE & Ready!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
