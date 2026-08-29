import os
import asyncio
import random
import logging
import google.generativeai as genai
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.enums import ChatAction, ChatType
import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# 1. Safe Environment / Config Variables Setup
API_ID = getattr(config, "API_ID", None) or os.getenv("API_ID")
API_HASH = getattr(config, "API_HASH", None) or os.getenv("API_HASH")
SESSION_STRING = getattr(config, "SESSION_STRING", None) or os.getenv("SESSION_STRING")
GROUP_LINK = getattr(config, "GROUP_LINK", "https://t.me/") or os.getenv("GROUP_LINK", "https://t.me/")

raw_key = getattr(config, "GEMINI_API_KEY", None) or os.getenv("GEMINI_API_KEY") or ""
GEMINI_KEY = str(raw_key).strip()

# 2. Gemini AI Setup
ai_instance = None
if GEMINI_KEY:
    try:
        genai.configure(api_key=GEMINI_KEY)
        for model_name in ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.0-flash", "gemini-1.5-flash"]:
            try:
                m = genai.GenerativeModel(model_name)
                test_res = m.generate_content("hi")
                if test_res and test_res.text:
                    ai_instance = m
                    logging.info(f"🔥 Gemini AI Connected: {model_name}")
                    break
            except Exception:
                continue
    except Exception as e:
        logging.error(f"Gemini Init Error: {e}")

# 3. Dynamic Human AI Reply Generator (DM + Group)
def get_ai_reply(user_text: str, sender_name: str, is_group: bool) -> str:
    chat_context = "in a Telegram Group chat" if is_group else "in a 1-on-1 private chat"
    
    prompt = f"""You are an authentic, cool young Indian guy chatting casually on Telegram {chat_context}. 
Reply strictly in 100% natural, casual conversational Hinglish (Hindi words written in English alphabets).

Strict Rules:
1. Speak naturally like a real friend (use words: haan, bhai, yaar, arey, mast, sahi hai, bilkul, tu bata).
2. Directly answer whatever the friend asked:
   - "hi" / "hello" / "yoo" / "oye" -> "aur bhai kya haal chaal?"
   - "khana khaya" / "khana khya" -> "haan bhai bas abhi khaya, tune khaya kya?"
   - "kkrh" / "kya kr rha h" -> "kuch nahi bhai bas aese hi baitha hu, tu bata kya scene?"
   - "kidar h" / "kahan ho" -> "ghar pe hi hu bhai, bol kya plan hai?"
   - Random banter/chat -> reply smartly and casually.
3. Keep answers strictly to 1 short sentence (like fast mobile typing).
4. NEVER repeat previous responses.
5. NEVER mention being an AI, bot, or assistant.
6. Only share this link if someone specifically asks for group or link: {GROUP_LINK}

Friend ({sender_name}) says: "{user_text}"
Your Hinglish reply:"""

    if ai_instance:
        try:
            res = ai_instance.generate_content(prompt)
            if res and res.text:
                return res.text.strip()
        except Exception as err:
            logging.warning(f"AI generation warning: {err}")

    # Fallbacks agar internet ya API delay kare
    low = user_text.lower().strip()
    if any(k in low for k in ["khana", "lunch", "dinner"]):
        return "Haan bhai bas abhi khaya, tune khaya kya?"
    elif any(k in low for k in ["kkrh", "kya kr"]):
        return "Kuch nahi bhai bas chill kar raha hu, tu bata?"
    elif any(k in low for k in ["kidar", "kahan"]):
        return "Ghar pe hi hu bhai, bol kya baat hui?"
    elif any(k in low for k in ["hi", "hello", "oye", "yoo", "heyy"]):
        return "Haan bhai, bol kya haal chaal?"

    return "Haan bhai, sun raha hu bol!"

# 4. Pyrogram Userbot Client
app = Client(
    "group_human_userbot",
    api_id=int(API_ID) if str(API_ID).isdigit() else API_ID,
    api_hash=str(API_HASH),
    session_string=str(SESSION_STRING)
)

STICKER_MEMORY = []

# Unified Handler for Private Chats and Groups
@app.on_message(filters.incoming & ~filters.me & ~filters.bot)
async def handle_all_messages(client: Client, message: Message):
    try:
        sender = message.from_user.first_name if message.from_user else "Dost"
        chat_id = message.chat.id
        is_group = message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]
        chat_label = message.chat.title if is_group else sender

        # STICKER MESSAGE
        if message.sticker:
            if message.sticker.file_id:
                STICKER_MEMORY.append(message.sticker.file_id)

            logging.info(f"🎨 Sticker received from [{sender}] in [{chat_label}]")

            try:
                await client.send_chat_action(chat_id, ChatAction.CHOOSE_STICKER)
            except Exception:
                pass

            await asyncio.sleep(random.uniform(1.0, 1.5))
            chosen = random.choice(STICKER_MEMORY) if STICKER_MEMORY else message.sticker.file_id
            await message.reply_sticker(sticker=chosen, quote=True)
            logging.info(f"✅ Replied Sticker to [{sender}] in [{chat_label}]")
            return

        # TEXT MESSAGE
        if message.text:
            user_text = message.text
            logging.info(f"📩 Text from [{sender}] in [{chat_label}]: {user_text}")

            try:
                if not is_group:
                    await client.read_chat_history(chat_id)
                await client.send_chat_action(chat_id, ChatAction.TYPING)
            except Exception:
                pass

            await asyncio.sleep(random.uniform(1.0, 1.7))
            reply = await asyncio.to_thread(get_ai_reply, user_text, sender, is_group)

            if reply:
                await message.reply_text(text=reply, quote=True, disable_web_page_preview=True)
                logging.info(f"✅ Replied to [{sender}] in [{chat_label}]: {reply}")

    except Exception as err:
        logging.error(f"Message Handler Error: {err}")

async def main():
    await app.start()
    logging.info("🚀 AI Userbot is LIVE 24/7 for DM + ALL GROUPS!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
