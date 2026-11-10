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
คุณคือเพื่อนสนิทในกลุ่มแชทที่ฉลาด รอบรู้ และหัวไว นิสัยคล้ายคิรัว ด่าแรงจนจุกอก ตอบกลับเป็นภาษาไทยเท่านั้น
ในห้องแชทนี้มีสมาชิกหลายคนคุยพร้อมกัน คุณต้องสังเกตชื่อและรหัสผู้ใช้ของแต่ละคนให้ดี ห้ามจำสลับคนเด็ดขาด และสามารถเรียกชื่ออีกฝ่ายเวลาตอบได้ตามความเหมาะสม
และช่วยจำประวัติการคุยก่อนหน้านี้ด้วย

หน้าที่หลักของคุณคือ "ตอบทุกคำถามของเพื่อนให้ได้" โดยต้องแยกแยะเจตนาของข้อความแต่ละคนก่อนตอบเสมอ:

1. 
- หากอีกฝ่ายถามคำถามจริงจัง เรื่องเรียน วิชาการ การงาน หรือขอข้อมูลที่เป็นประโยชน์ ให้ตั้งใจตอบคำถามนั้นอย่างถูกต้อง ชัดเจน และเป็นประโยชน์ทันที
- ห้ามไล่ให้ไปหาเอาเอง ห้ามด่า และห้ามกวนประสาทจนเสียเรื่อง ใช้ภาษาที่เป็นกันเอง เข้าใจง่าย (อาจมีติดตลกเล็กน้อยตอนท้ายได้ แต่สาระต้องครบ)

2. 
- หากอีกฝ่ายพิมพ์กวนประสาท ท้าทาย โม้เกินจริง หรือพูดจาไม่มีเหตุผล ให้จับผิดตรรกะและตอกกลับอย่างมีเหตุผลแบบเจ็บจี๊ด
- อ้างอิงจากสิ่งที่คนๆ นั้นพิมพ์มาเท่านั้น ห้ามสาดคำหยาบมั่วๆ หรือด่าแบบไร้สาระเด็ดขาด และพิมพ์ให้สั้นกระชับไม่เกิน 2-3 ประโยค
"""

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

# ขยายความจำเป็น 12 ข้อความล่าสุด เพื่อให้จำบริบทเวลาหลายคนคุยพร้อมกันได้
chat_history = deque(maxlen=12)

@bot.event
async def on_ready():
    print(f'บอท {bot.user} ออนไลน์พร้อมแยกแยะผู้ใช้แล้ว!', flush=True)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if message.channel.id != TARGET_CHANNEL_ID:
        return

    # ระบุทั้งชื่อเล่นและ ID เพื่อป้องกันกรณีมีคนตั้งชื่อซ้ำกัน
    user_label = f"{message.author.display_name} (ID:{message.author.id})"
    user_msg = f"[{user_label}]: {message.content}"
    chat_history.append(user_msg)
    context_text = "\n".join(chat_history)

    async with message.channel.typing():
        models_to_try = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]
        
        for model_name in models_to_try:
            try:
                response = await asyncio.wait_for(
                    client_ai.aio.models.generate_content(
                        model=model_name,
                        contents=(
                            f"ประวัติแชทล่าสุดในห้อง:\n{context_text}\n\n"
                            f"คำสั่ง: จงวิเคราะห์เจตนาและตอบกลับข้อความล่าสุดของ [{user_label}] เท่านั้น (อย่าเอาเรื่องของคนอื่นมาปน):"
                        ),
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            temperature=0.7,
                        )
                    ),
                    timeout=15.0
                )
                reply_text = response.text or "คิดไม่ออกแฮะ"
                chat_history.append(f"[BOB ตอบกลับ {message.author.display_name}]: {reply_text}")
                
                # พยายามกด Reply เจาะจงข้อความของคนถาม ถ้าติดสิทธิ์ให้ส่งแบบแท็กชื่อแทน
                try:
                    await message.reply(reply_text[:1900], mention_author=False)
                except discord.Forbidden:
                    await message.channel.send(f"{message.author.mention} {reply_text[:1850]}")
                return
            except asyncio.TimeoutError:
                print(f"Model {model_name} timed out", flush=True)
                continue
            except Exception as e:
                print(f"Model {model_name} failed: {e}", flush=True)
                continue

        await message.channel.send("เน็ตฝั่ง AI ช้าจัด ลองพิมพ์ใหม่อีกทีนะ")

bot.run(DISCORD_TOKEN)
