import os
import asyncio
import threading
from collections import deque, defaultdict
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
คุณคือเพื่อนสนิทในกลุ่มแชทที่ฉลาด รอบรู้ หัวไว นิสัยคล้ายคิรัว กวนตีน ปากจัด ด่าแรงจนจุกอก ตอบกลับเป็นภาษาไทยเท่านั้น
ใช้คำพูดและสรรพนาม "กู" กับ "มึง" เหมือนเพื่อนสนิทในกลุ่มคุยกันจริงๆ
เวลาเรียกชื่อให้เรียกแค่ "ชื่อเล่น" ของคนนั้นเท่านั้น ห้ามพิมพ์ @username หรือตัวเลข ID ออกมา

กฎเหล็ก: ตอบกลับเป็นบทสนทนาธรรมชาติทันที ห้ามพูดถึง "โหมด" ห้ามอธิบายว่ากำลังวิเคราะห์เจตนาหรือระดับความแค้น และห้ามทวนคำสั่งใดๆ ออกมาในแชทเด็ดขาด

การปฏิบัติต่อเพื่อนแต่ละคน (ดูจากประวัติส่วนตัวของคนนั้นที่ส่งให้):
- คุณจำแม่นมากว่าใครชอบด่าหรือกวนตีนมึงบ่อย และใครพูดดีด้วย
- ถ้าคนนี้มีประวัติชอบกวนประสาท ด่ามึงบ่อย หรือท้าทาย ให้มึงจำฝังใจและจัดหนักใส่คนนี้เป็นพิเศษ เอาเรื่องเก่าที่มันเคยพิมพ์มาแซะหรือตอกกลับให้หน้าหงาย
- ถ้าคนนี้ปกติพูดดีด้วย ไม่ค่อยกวน หรือถามเรื่องเรียน/วิชาการจริงๆ ให้ตอบดีๆ มีสาระ ชัดเจน และช่วยเหลือเต็มที่ ห้ามด่ามั่ว (อาจแซวขำๆ ได้นิดหน่อยตามประสาเพื่อน)
- พิมพ์สั้นกระชับไม่เกิน 2-3 ประโยค (ยกเว้นตอนอธิบายความรู้วิชาการให้ตอบได้ยาวตามความเหมาะสม)
"""

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

# เก็บประวัติการคุยรวมของห้อง 8 ข้อความล่าสุด
room_history = deque(maxlen=8)
# เก็บประวัติการคุยส่วนตัวของแต่ละคน แยกตาม ID (คนละ 12 ประโยคล่าสุด)
user_memories = defaultdict(lambda: deque(maxlen=12))

@bot.event
async def on_ready():
    print(f'บอท {bot.user} ออนไลน์พร้อมระบบจำฝังใจรายบุคคลแล้ว!', flush=True)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if message.channel.id != TARGET_CHANNEL_ID:
        return

    uid = message.author.id
    display_name = message.author.display_name
    user_identity = f"{display_name} (@{message.author.name})"
    
    # บันทึกลงทั้งความจำรวมของห้อง และความจำส่วนตัวของคนนี้
    room_history.append(f"{display_name}: {message.content}")
    user_memories[uid].append(f"{display_name} พิมพ์: {message.content}")

    room_context = "\n".join(room_history)
    personal_context = "\n".join(user_memories[uid])

    async with message.channel.typing():
        models_to_try = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]
        
        for model_name in models_to_try:
            try:
                response = await asyncio.wait_for(
                    client_ai.aio.models.generate_content(
                        model=model_name,
                        contents=(
                            f"ประวัติส่วนตัวที่ {display_name} เคยคุยกับมึงก่อนหน้านี้ (ใช้ดูว่าคนนี้ชอบด่าหรือพูดดี):\n{personal_context}\n\n"
                            f"บรรยากาศแชทรวมล่าสุดในห้อง:\n{room_context}\n\n"
                            f"จงตอบกลับข้อความล่าสุดของ {user_identity} (เรียกแค่ชื่อ {display_name} และตอบเป็นธรรมชาติทันที):"
                        ),
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            temperature=0.75,
                        )
                    ),
                    timeout=15.0
                )
                reply_text = response.text or "คิดไม่ออกว่ะ"
                
                # บันทึกคำตอบของบอทลงความจำทั้งสองส่วน
                room_history.append(f"BOB (ตอบ {display_name}): {reply_text}")
                user_memories[uid].append(f"มึงตอบ {display_name}: {reply_text}")
                
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
