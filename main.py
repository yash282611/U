import asyncio
import random
import logging
import json
import urllib.request
import urllib.error
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from config import API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY, GROUP_LINK

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Pure Dynamic AI Generator
def get_ai_reply(user_text: str, sender_name: str) -> str:
    prompt_text = (
        f"You are a real Indian person chatting casually with a friend on Telegram.\n"
        f"Guidelines:\n"
        f"1. Reply strictly in natural, everyday casual Hinglish (Hindi words in English script).\n"
        f"2. Keep your answer short (1-2 sentences), friendly, and conversational.\n"
        f"3. Understand short-forms and slang (e.g., kkrh = kya kar rahe ho, kaisa h = kaisa hai, oye, wrud, etc.) and reply accordingly.\n"
        f"4. Never say you are an AI or bot. Speak like a real human.\n"
        f"5. Only if the user asks for a group link or channel, provide: {GROUP_LINK}\n\n"
        f"Message from {sender_name}: {user_text}\n"
        f"Your direct Hinglish reply:"
    )

    models_to_try = [
        "gemini-1.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-pro",
        "gemini-pro"
    ]

    for model_name in models_to_try:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": prompt_text}]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.9,
                    "maxOutputTokens": 100
                }
            }
            
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data_bytes, headers={"Content-Type": "application/json"})
            
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                reply = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                if reply:
                    return reply

        except urllib.error.HTTPError as http_err:
            error_body = http_err.read().decode("utf-8", errors="ignore")
            logging.error(f"HTTP Error on {model_name}: {http_err.code} - {error_body}")
            continue
        except Exception as e:
            logging.error(f"Error on {model_name}: {e}")
            continue

    return ""

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

        # Seen & Typing Simulation
        try:
            await client.read_chat_history(chat_id)
            await client.send_chat_action(chat_id, ChatAction.TYPING)
        except Exception:
            pass

        # Human-like delay
        await asyncio.sleep(random.uniform(1.2, 2.2))

        # Dynamic AI Response
        reply_text = await asyncio.to_thread(get_ai_reply, user_text, sender)

        if reply_text:
            await message.reply_text(text=reply_text, quote=True, disable_web_page_preview=True)
            logging.info(f"✅ AI Replied to [{sender}]: {reply_text}")

    except Exception as e:
        logging.error(f"Message handler error: {e}")

async def main():
    await app.start()
    logging.info("⏳ Dialogs cache load ho raha hai...")
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
