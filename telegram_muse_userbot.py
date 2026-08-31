import os
import json
import base64
import asyncio
import aiohttp
from telethon import TelegramClient, events
from collections import defaultdict

API_ID = int(os.getenv("TG_API_ID", "0"))
API_HASH = os.getenv("TG_API_HASH", "")
SESSION_NAME = "muse_spark_session"
OPENCODE_API_KEY = os.getenv("OPENCODE_API_KEY", "")
if os.getenv("TG_SESSION_B64"):
    try:
        with open(f"{SESSION_NAME}.session", "wb") as f:
            f.write(base64.b64decode(os.getenv("TG_SESSION_B64")))
    except:
        pass
MODEL = "muse-spark-1.2-contributor-free"
OPENCODE_API_URL = "https://opencode.ai/zen/v1/responses"
MEMORY_FILE = "muse_memory.json"
MAX_HISTORY = 20

SYSTEM_PROMPT = "You are Muse Spark 1.2, helpful AI assistant. Answer concisely and helpfully. Remember previous conversation."

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

try:
    with open(MEMORY_FILE, "r") as f:
        memory = defaultdict(list, {int(k): v for k, v in json.load(f).items()})
except:
    memory = defaultdict(list)

def save_memory():
    try:
        with open(MEMORY_FILE, "w") as f:
            json.dump({str(k): v for k, v in memory.items()}, f, ensure_ascii=False)
    except:
        pass

async def ask_muse(chat_id: int, prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {OPENCODE_API_KEY}",
        "Content-Type": "application/json"
    }
    history = memory[chat_id][-MAX_HISTORY:]
    conv = "\n".join([f"{'User' if m['role']=='user' else 'Assistant'}: {m['content']}" for m in history])
    full_input = f"{SYSTEM_PROMPT}\n\nConversation history:\n{conv}\n\nUser: {prompt}\nAssistant:" if conv else f"{SYSTEM_PROMPT}\n\nUser: {prompt}"
    payload = {
        "model": MODEL,
        "input": full_input,
        "reasoning": {"effort": "medium"}
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(OPENCODE_API_URL, headers=headers, json=payload) as resp:
            data = await resp.json()
            text = None
            if data.get("status") == "completed":
                for item in data.get("output", []):
                    if item.get("type") == "message" and item.get("role") == "assistant":
                        for c in item.get("content", []):
                            if c.get("type") == "output_text":
                                text = c.get("text", "")
            if not text:
                if "error" in data and data["error"]:
                    text = f"Error: {data['error']}"
                else:
                    text = f"Error: {data}"
            memory[chat_id].append({"role": "user", "content": prompt})
            memory[chat_id].append({"role": "assistant", "content": text})
            if len(memory[chat_id]) > MAX_HISTORY:
                memory[chat_id] = memory[chat_id][-MAX_HISTORY:]
            save_memory()
            return text

@client.on(events.NewMessage(incoming=True))
async def handler(event):
    if not event.is_private:
        return
    if event.sender and event.sender.bot:
        return
    me = await client.get_me()
    if event.sender_id == me.id:
        return
    if not event.text:
        return
    txt = event.text.strip()
    if txt == "/clear":
        memory[event.chat_id] = []
        save_memory()
        await event.respond("✅ Hafeze pak shod! 🧠🗑️")
        return
    if txt == "/help":
        await event.respond("🧠 Memory faale! Harچی بگی یادم میمونه.\n/clear = pak kardan hafeze\n/help = rahnama")
        return
    if txt.startswith("/") and len(txt) > 1:
        return

    async with client.action(event.chat_id, 'typing'):
        try:
            await asyncio.sleep(1)
            reply = await ask_muse(event.chat_id, txt)
            await event.respond(reply)
            print(f"Replied to {event.sender_id}: {txt[:40]}")
        except Exception as e:
            print(f"Error: {e}")
            await event.respond("Sorry, ye error pish umad, dobare talash kon 🙏")

if __name__ == "__main__":
    print("Bot started... Listening only to PMs 🚀")
    client.start()
    client.run_until_disconnected()
