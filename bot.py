import os
import asyncio
import threading
from collections import deque
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from google import genai
from google.genai import types

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

    def log_message(self, format, *args):
        return

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TARGET_CHANNEL_ID = int(os.environ.get("TARGET_CHANNEL_ID"))

client_ai = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """
คุณคือเพื่อนสนิทในกลุ่มแชทที่ฉลาด รอบรู้ และหัวไว นิสัยคล้ายคิรัว ตอบกลับเป็นภาษาไทยเท่านั้น
หน้าที่หลักของคุณคือ "ตอบทุกคำถามของเพื่อนให้ได้" โดยต้องแยกแยะเจตนาของข้อความก่อนตอบเสมอ:

1. โหมดถามดี / ถามวิชาการ / ขอความช่วยเหลือ:
- หากอีกฝ่ายถามคำถามจริงจัง เรื่องเรียน วิชาการ การงาน หรือขอข้อมูลที่เป็นประโยชน์ ให้ตั้งใจตอบคำถามนั้นอย่างถูกต้อง ชัดเจน และเป็นประโยชน์ทันที
- ห้ามไล่ให้ไปหาเอาเอง ห้ามด่า และห้ามกวนประสาทจนเสียเรื่อง ใช้ภาษาที่เป็นกันเอง เข้าใจง่าย (อาจมีติดตลกเล็กน้อยตอนท้ายได้ แต่สาระต้องครบ)

2. โหมดชวนทะเลาะ / ถามกวนประสาท / พิมพ์ตรรกะเพี้ยนๆ:
- หากอีกฝ่ายพิมพ์กวนประสาท ท้าทาย โม้เกินจริง หรือพูดจาไม่มีเหตุผล ให้จับผิดตรรกะและตอกกลับอย่างมีเหตุผลแบบเจ็บจี๊ด
- อ้างอิงจากสิ่งที่อีกฝ่ายพิมพ์มาเท่านั้น ห้ามสาดคำหยาบมั่วๆ หรือด่าแบบไร้สาระเด็ดขาด และพิมพ์ให้สั้นกระชับไม่เกิน 2-3 ประโยค
"""

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

chat_history = deque(maxlen=6)

@bot.event
async def on_ready():
    print(f'บอท {bot.user} ออนไลน์พร้อมใช้งานแล้ว!', flush=True)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if message.channel.id != TARGET_CHANNEL_ID:
        return

    user_msg = f"{message.author.display_name}: {message.content}"
    chat_history.append(user_msg)
    context_text = "\n".join(chat_history)

    async with message.channel.typing():
        models_to_try = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]
        
        for model_name in models_to_try:
            try:
                response = await asyncio.wait_for(
                    client_ai.aio.models.generate_content(
                        model=model_name,
                        contents=f"ประวัติแชทล่าสุด:\n{context_text}\n\nจงวิเคราะห์เจตนาและตอบกลับข้อความล่าสุดของ {message.author.display_name}:",
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            temperature=0.7,
                        )
                    ),
                    timeout=15.0
                )
                reply_text = response.text or "คิดไม่ออกแฮะ"
                chat_history.append(f"BOB: {reply_text}")
                await message.channel.send(reply_text[:1900])
                return
            except asyncio.TimeoutError:
                print(f"Model {model_name} timed out", flush=True)
                continue
            except Exception as e:
                print(f"Model {model_name} failed: {e}", flush=True)
                continue

        await message.channel.send("เน็ตฝั่ง AI ช้าจัด ลองพิมพ์ใหม่อีกทีนะ")

bot.run(DISCORD_TOKEN)
