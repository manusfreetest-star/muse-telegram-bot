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
if os.getenv("TG_SESSION_B64_1"):
    try:
        b64 = os.getenv("TG_SESSION_B64_1", "") + os.getenv("TG_SESSION_B64_2", "")
        with open(f"{SESSION_NAME}.session", "wb") as f:
            f.write(base64.b64decode(b64))
    except:
        pass
elif os.getenv("TG_SESSION_B64"):
    try:
        with open(f"{SESSION_NAME}.session", "wb") as f:
            f.write(base64.b64decode(os.getenv("TG_SESSION_B64")))
    except:
        pass
MODEL = "muse-spark-1.2-contributor-free"
OPENCODE_API_URL = "https://opencode.ai/zen/v1/responses"
MEMORY_FILE = "muse_memory.json"
MAX_HISTORY = 20

ADMIN_ID = 8470803779
PA_API_TOKEN = os.getenv("PA_API_TOKEN", "5fa51ff1e2f81e21eae4dec923793f3605ffdafb")
PA_USERNAME = os.getenv("PA_USERNAME", "luxuryfarsi")

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
    low = txt.lower()
    if ("pythonanywhere" in low and "run" in low) or ("pa run" in low):
        if event.sender_id != ADMIN_ID:
            await event.respond("❌ Shoma admin nistid! Faghat admin (8470803779) mitune az in plugin estefade kone 🔒")
            return
        code = None
        if "```" in txt:
            try:
                code = txt.split("```")[1]
                if code.startswith("python"):
                    code = code[6:]
                code = code.strip()
            except:
                code = None
        if not code:
            await event.respond("📝 Lotfan code ro be soorate ```python\nCODE\n``` befrest ta rooye PythonAnywhere run konam 🚀")
            return
        await event.respond("⏳ Dar hal upload va run rooye PythonAnywhere... 🚀")
        try:
            safe_name = f"admin_run_{event.chat_id}.py"
            async with aiohttp.ClientSession() as s:
                await s.post(f"https://www.pythonanywhere.com/api/v0/user/{PA_USERNAME}/files/path/home/{PA_USERNAME}/{safe_name}", headers={"Authorization": f"Token {PA_API_TOKEN}"}, data={"content": code})
            with open(f"/tmp/{safe_name}", "w") as f:
                f.write(code)
            proc2 = await asyncio.create_subprocess_exec("python3", f"/tmp/{safe_name}", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await asyncio.wait_for(proc2.communicate(), timeout=15)
                out = stdout.decode()[:3000] if stdout else ""
                err = stderr.decode()[:1500] if stderr else ""
                result = f"✅ Run shod!\n\n📤 Output:\n```\n{out or '(no output)'}\n```"
                if err:
                    result += f"\n\n⚠️ Error:\n```\n{err}\n```"
                await event.respond(result)
        except Exception as e:
            await event.respond(f"❌ Error dar run: {e}")
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
