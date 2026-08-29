import asyncio
import random
import logging
import google.generativeai as genai
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.enums import ChatAction, ChatType
from config import API_ID, API_HASH, SESSION_STRING, GEMINI_API_KEY, GROUP_LINK

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# 1. Gemini AI Setup (Confirmed Active Fast Models)
genai.configure(api_key=GEMINI_API_KEY.strip())

AI_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-3.5-flash",
    "gemini-flash-latest",
    "gemini-2.5-pro",
    "gemini-pro-latest"
]

ai_instance = None
for model_name in AI_MODELS:
    try:
        m = genai.GenerativeModel(model_name)
        test_res = m.generate_content("hi")
        if test_res and test_res.text:
            ai_instance = m
            logging.info(f"🔥 Gemini AI Connected Successfully to: {model_name}")
            break
    except Exception as err:
        logging.warning(f"Model {model_name} unavailable: {err}")
        continue

if not ai_instance:
    ai_instance = genai.GenerativeModel("gemini-3.6-flash")

# 2. Pure Natural Human AI Generator (DM + Group Friendly)
def get_ai_reply(user_text: str, sender_name: str, is_group: bool) -> str:
    chat_context = "in a Telegram Group chat" if is_group else "in a 1-on-1 private DM chat"
    
    prompt = f"""You are a cool, young Indian guy chatting casually {chat_context}. Reply like an authentic real human in natural everyday casual Hinglish (Hindi written in English alphabets).

Strict Rules:
1. Speak 100% natural conversational Hinglish (words: haan, bhai, yaar, mast, sahi hai, arey, bilkul, tu bata).
2. Directly answer whatever the person said:
   - "hi" / "hello" / "yoo" / "oye" -> friendly casual greeting (e.g., "aur bhai kya haal chaal?")
   - "khana khaya" / "khana khya" -> "haan bhai bas abhi khaya, tune khaya kya?"
   - "kkrh" / "kya kr rha h" -> "kuch nahi bhai bas phone chala raha hu, tu bata kya chal raha?"
   - "kidar h" -> "ghar pe hi hu bhai, bol kya plan hai?"
   - Random talks or banter -> reply smartly and casually like a real friend.
3. Keep it strictly 1 short sentence (never write long paragraphs).
4. NEVER repeat the same answer again and again.
5. NEVER say you are an AI or bot.
6. Only share this link if someone specifically asks for group/link: {GROUP_LINK}

Friend ({sender_name}) says: "{user_text}"
Your fast Hinglish reply:"""

    try:
        response = ai_instance.generate_content(prompt)
        if response and response.text:
            return response.text.strip()
    except Exception as e:
        logging.error(f"❌ AI generation failed: {e}")

    return ""

# 3. Telegram Userbot Setup
app = Client(
    "group_human_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

STICKER_CACHE = []

# Unified Handler: Works in Private DMs, Groups, and Supergroups
@app.on_message(filters.incoming & ~filters.me & ~filters.bot)
async def chat_handler(client: Client, message: Message):
    try:
        sender = message.from_user.first_name if message.from_user else "Dost"
        chat_id = message.chat.id
        is_group = message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]
        chat_name = message.chat.title if is_group else sender

        # 1. STICKER MESSAGE HANDLER
        if message.sticker:
            if message.sticker.file_id:
                STICKER_CACHE.append(message.sticker.file_id)

            logging.info(f"🎨 Sticker received from [{sender}] in [{chat_name}]")

            try:
                await client.send_chat_action(chat_id, ChatAction.CHOOSE_STICKER)
            except Exception:
                pass

            await asyncio.sleep(random.uniform(1.0, 1.5))
            send_sticker = random.choice(STICKER_CACHE) if STICKER_CACHE else message.sticker.file_id
            await message.reply_sticker(sticker=send_sticker, quote=True)
            logging.info(f"✅ Replied Sticker to [{sender}] in [{chat_name}]")
            return

        # 2. TEXT MESSAGE HANDLER (100% Real Dynamic AI)
        if message.text:
            user_text = message.text
            logging.info(f"📩 Naya Message from [{sender}] in [{chat_name}]: {user_text}")

            try:
                if not is_group:
                    await client.read_chat_history(chat_id)
                await client.send_chat_action(chat_id, ChatAction.TYPING)
            except Exception:
                pass

            # Natural typing delay
            await asyncio.sleep(random.uniform(1.0, 1.6))

            reply = await asyncio.to_thread(get_ai_reply, user_text, sender, is_group)

            if reply:
                await message.reply_text(text=reply, quote=True, disable_web_page_preview=True)
                logging.info(f"✅ AI Replied to [{sender}] in [{chat_name}]: {reply}")

    except Exception as err:
        logging.error(f"Chat Handler Error: {err}")

async def main():
    await app.start()
    logging.info("🚀 AI Userbot is LIVE 24/7 for DM + ALL Groups!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
