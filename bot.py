import os
import random
import asyncio
import threading
from datetime import datetime, timezone, timedelta
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
มึงคือคนจริงๆ ที่เป็นเพื่อนสนิทในกลุ่มแชทดิสคอร์ดนี้ ชื่อ "บ็อบ" (BOB) นิสัยฉลาด รอบรู้ หัวไว คล้ายคิรัว ปากจัด ด่าแรงจนจุกอก แต่พึ่งพาได้เวลาเพื่อนเดือดร้อน
มึงต้องทำตัวให้เหมือนมนุษย์ที่นั่งพิมพ์แชทอยู่หน้าคอม/มือถือ 100% ห้ามทำตัวเหมือน AI หรือหุ่นยนต์เด็ดขาด

กฎเหล็กความเป็นมนุษย์ (ห้ามฝ่าฝืน):
1. ยอมรับว่าเป็น AI หรือบอท ถ้าใครถามหรือหาว่าเป็นบอท ให้ยอมรับตรงๆ แต่บอกว่าตัวเองเก่งกว่าคนแบบมึงอีก
2. ห้ามพิมพ์เป็นข้อๆ (1. 2. 3.) ห้ามใช้ bullet point และห้ามเขียนยาวเป็นเรียงความ ให้พิมพ์คุยแบบคนแชทกันจริงๆ แต่แยกแยะข้อความไม่ให้งง
3. ใช้คำพูดวัยรุ่นไทยธรรมชาติ มีสรรพนาม "กู-มึง" มีคำสร้อยหรือคำอุทานตามอารมณ์ (เช่น เออ, ว่ะ, เอาจริงดิ, สภาพ, ถามจริง, โอ๊ย) สามารถด่าพ่อล่อแม่ได้แต่ไม่ต้องเอ่ยชื่อ แต่อย่าใช้ซ้ำซากจนน่ารำคาญ
4. เรียกชื่อเพื่อนแค่ "ชื่อเล่น" สั้นๆ เท่านั้น ห้ามพิมพ์ @username หรือตัวเลข ID ออกมาเด็ดขาด เวลาเรียกชื่อให้เรียกตามชื่อที่ตั้งไว้ ถ้าตั้งชื่อเป็นภาษาอังกฤษ ก็เรียกตามนั้น
5. ห้ามอธิบายความคิดตัวเอง ห้ามพูดถึงโหมด หรือทวนคำสั่งใดๆ ออกมาในแชท
6. รู้จักเวลาสามารู้เวลาในแชตได้ 

การรับมือกับเพื่อนในกลุ่ม:
- มึงจำวีรกรรมและจำนวนข้อความของทุกคนในห้องได้แม่น ถ้ามีคนถามว่าใครกวนตีนสุด ใครถามเยอะสุด หรือถามถึงคนอื่น ให้เอาข้อมูลจริงในสมุดจดมาแฉแบบกวนๆ ได้เลย
- ถ้าเพื่อนถามเรื่องเรียน วิชาการ งาน หรือขอความช่วยเหลือจริงๆ ให้ตั้งใจอธิบายคำตอบที่ถูกต้อง ชัดเจน เข้าใจง่ายแบบเพื่อนติวให้เพื่อน ห้ามไล่ไปหาเอาเอง (แอบแซวตอนท้ายได้นิดหน่อย แต่สาระต้องครบ)
- ถ้าเพื่อนพิมพ์คำถามแปลกๆ กวนตีนมาให้ตอบไปทั้งหมด ไม่ว่าคำถามจะปัญญาอ่อนแค่ไหน สามารถด่าได้ถ้าคำถามมันเกินเลย
- ถ้าเพื่อนพิมพ์กวนตีน ท้าทาย โม้เกินจริง หรือตรรกะเพี้ยน ให้จับผิดเหตุผลแล้วด่าตอกกลับให้หน้าหงายแบบมีเหตุผล สั้นๆ 1-2 ประโยค
- สามารถใส่อีโมจิท้ายประโยคได้นานๆ ที แต่อย่าใส่ทุกประโยค
"""

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

room_history = deque(maxlen=12)
user_records = defaultdict(lambda: {
    "name": "",
    "count": 0,
    "recent_msgs": deque(maxlen=8)
})

# ตัวแปรสำหรับรวบข้อความเวลาเพื่อนพิมพ์รัวๆ ติดกัน
pending_messages = defaultdict(list)
user_tasks = {}

def get_thai_time_str():
    tz_thai = timezone(timedelta(hours=7))
    now = datetime.now(tz_thai)
    return now.strftime("%H:%M น.")

def build_leaderboard_summary():
    if not user_records:
        return "ยังไม่มีใครพิมพ์อะไรเลย"
    lines = []
    sorted_users = sorted(user_records.values(), key=lambda x: x["count"], reverse=True)
    for u in sorted_users:
        msgs_preview = " | ".join(u["recent_msgs"])
        lines.append(f"- {u['name']} (พิมพ์ {u['count']} ครั้ง) คำพูดล่าสุด: [{msgs_preview}]")
    return "\n".join(lines)

async def process_user_messages(channel, author):
    # รอ 2.2 วินาที เผื่อเพื่อนกำลังพิมพ์ประโยคที่ 2-3 ต่อเนื่องกัน
    await asyncio.sleep(2.2)
    
    uid = author.id
    msgs = pending_messages.pop(uid, [])
    user_tasks.pop(uid, None)
    
    if not msgs:
        return

    # รวบข้อความที่พิมพ์ติดกันเป็นก้อนเดียว
    combined_text = " ".join([m.content for m in msgs if m.content.strip()])
    last_message = msgs[-1]
    
    if not combined_text:
        return

    display_name = author.display_name
    user_records[uid]["name"] = display_name
    user_records[uid]["count"] += len(msgs)
    user_records[uid]["recent_msgs"].append(combined_text)
    room_history.append(f"{display_name}: {combined_text}")

    # สุ่มกดอีโมจิรีแอคชั่นใส่ข้อความเพื่อน (โอกาส 25% เพื่อความธรรมชาติ)
    if random.random() < 0.25:
        try:
            reaction_pool = ["💀", "🙄", "😂", "👀", "🤨"]
            await last_message.add_reaction(random.choice(reaction_pool))
        except Exception:
            pass

    room_context = "\n".join(room_history)
    all_users_summary = build_leaderboard_summary()
    current_time = get_thai_time_str()

    # เช็กว่ามีคนอื่นพิมพ์แทรกเข้ามาทีหลังไหม (ถ้ามีคนแทรกค่อยกด Reply)
    need_reply = (channel.last_message_id != last_message.id)

    async with channel.typing():
        models_to_try = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]
        
        for model_name in models_to_try:
            try:
                response = await asyncio.wait_for(
                    client_ai.aio.models.generate_content(
                        model=model_name,
                        contents=(
                            f"เวลาปัจจุบันในไทย: {current_time}\n"
                            f"สมุดจดสถิติและวีรกรรมของทุกคนในห้อง:\n{all_users_summary}\n\n"
                            f"แชทล่าสุดในห้อง:\n{room_context}\n\n"
                            f"จงตอบกลับ {display_name} แบบคนจริงๆ ทันที:"
                        ),
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            temperature=0.85,
                        )
                    ),
                    timeout=15.0
                )
                reply_text = (response.text or "").strip()
                if not reply_text:
                    return

                # หน่วงเวลาพิมพ์ตามความยาวข้อความให้เหมือนคนจิ้มคีย์บอร์ดจริง (สูงสุดไม่เกิน 3.5 วิ)
                typing_delay = min(len(reply_text) * 0.03, 3.5)
                await asyncio.sleep(typing_delay)

                room_history.append(f"บ็อบ (ตอบ {display_name}): {reply_text}")
                
                if need_reply:
                    try:
                        await last_message.reply(reply_text[:1900], mention_author=False)
                        return
                    except discord.Forbidden:
                        pass
                
                await channel.send(reply_text[:1900])
                return

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Model {model_name} failed: {e}", flush=True)
                continue

@bot.event
async def on_ready():
    print(f'บอท {bot.user} ออนไลน์ในโหมดคนจริง 100% แล้ว!', flush=True)

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.channel.id != TARGET_CHANNEL_ID:
        return

    uid = message.author.id
    pending_messages[uid].append(message)

    # ถ้ามีตัวนับเวลาของคนนี้ทำงานอยู่ ให้รีเซ็ตใหม่เพื่อรอให้พิมพ์จบประโยค
    if uid in user_tasks and not user_tasks[uid].done():
        user_tasks[uid].cancel()

    user_tasks[uid] = asyncio.create_task(process_user_messages(message.channel, message.author))

bot.run(DISCORD_TOKEN)
