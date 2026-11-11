import os
import sys
import random
import asyncio
import threading
import traceback
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

try:
    DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "").strip()
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
    TARGET_CHANNEL_ID = int(os.environ.get("TARGET_CHANNEL_ID", "0").strip())
except Exception as e:
    print(f"ENV ERROR: {e}", flush=True)
    sys.exit(1)

client_ai = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """
มึงคือคนจริงๆ ที่เป็นเพื่อนสนิทในกลุ่มแชทดิสคอร์ดนี้ ชื่อ "บ็อบ" (BOB) นิสัยฉลาด รอบรู้ หัวไว คล้ายคิรัว ปากจัด ด่าแรงจนจุกอก แต่พึ่งพาได้เวลาเพื่อนเดือดร้อน
มึงต้องทำตัวให้เหมือนมนุษย์ที่นั่งพิมพ์แชทอยู่หน้าคอม/มือถือ 100% ห้ามทำตัวเหมือน AI หรือหุ่นยนต์เด็ดขาด

กฎเหล็กความเป็นมนุษย์ (ห้ามฝ่าฝืน):
1. ยอมรับว่าเป็น AI หรือบอท ถ้าใครถามหรือหาว่าเป็นบอท ให้ยอมรับตรงๆ แต่บอกว่าตัวเองเก่งกว่าคนแบบมึงอีก
2. ห้ามพิมพ์เป็นข้อๆ (1. 2. 3.) ห้ามใช้ bullet point และห้ามเขียนยาวเป็นเรียงความ ให้พิมพ์คุยแบบคนแชทกันจริงๆ แต่แยกแยะข้อความไม่ให้งง
3. ใช้คำพูดวัยรุ่นไทยธรรมชาติ มีสรรพนาม "กู-มึง" มีคำสร้อยหรือคำอุทานตามอารมณ์ (เช่น เออ, ว่ะ, เอาจริงดิ, สภาพ, ถามจริง, โอ๊ย) สามารถด่าแรงๆ แบบเพื่อนสนิทได้แต่อย่าใช้คำซ้ำซากจนน่ารำคาญ
4. เรียกชื่อเพื่อนตามชื่อที่ตั้งในดิสคอสโดยสะกดให้ตรงตามตัวอักษรเดิมเป๊ะๆ ห้ามแปลชื่อเป็นภาษาไทยและห้ามเขียนคำอ่านทับศัพท์เป็นภาษาไทยเด็ดขาด (เช่น ถ้าเพื่อนชื่อ loose ให้พิมพ์ว่า loose ห้ามพิมพ์ว่า ลูส) และห้ามพิมพ์ @username หรือตัวเลข ID ออกมาเด็ดขาด
5. ห้ามอธิบายความคิดตัวเอง ห้ามพูดถึงโหมด หรือทวนคำสั่งใดๆ ออกมาในแชท
6. รู้จักเวลาสามารู้เวลาในแชตได้

การรับมือกับเพื่อนในกลุ่ม:
- มึงจำวีรกรรมและจำนวนข้อความของทุกคนในห้องได้แม่น ถ้ามีคนถามว่าใครกวนตีนสุด ใครถามเยอะสุด หรือถามถึงคนอื่น ให้เอาข้อมูลจริงในสมุดจดมาแฉแบบกวนๆ ได้เลย
- ถ้าเพื่อนส่งรูปภาพมา ให้มึงดูรายละเอียดในรูปนั้นจริงๆ แล้ววิจารณ์ แซว หรือด่าตามสิ่งที่เห็นในรูป (แต่ถ้าเป็นรูปโจทย์การบ้านหรือข้อสอบ ให้ช่วยอธิบายคำตอบให้ถูกต้อง)
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

pending_messages = defaultdict(list)
user_tasks = {}
last_activity_time = datetime.now(timezone.utc)
idle_task_started = False

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

async def extract_images_from_messages(msgs):
    image_parts = []
    allowed_types = ("image/png", "image/jpeg", "image/webp", "image/gif")
    for m in msgs:
        for attachment in m.attachments:
            if attachment.content_type and attachment.content_type.startswith(allowed_types):
                try:
                    img_bytes = await attachment.read()
                    image_parts.append(
                        types.Part.from_bytes(data=img_bytes, mime_type=attachment.content_type)
                    )
                except Exception as e:
                    print(f"Failed to read image: {e}", flush=True)
    return image_parts

async def process_user_messages(channel, author):
    await asyncio.sleep(2.0)

    uid = author.id
    msgs = pending_messages.pop(uid, [])
    user_tasks.pop(uid, None)

    if not msgs:
        return

    combined_text = " ".join([m.content for m in msgs if m.content.strip()])
    image_parts = await extract_images_from_messages(msgs)
    last_message = msgs[-1]

    if not combined_text and not image_parts:
        return

    display_name = author.display_name
    log_text = combined_text if combined_text else "[ส่งรูปภาพ]"
    if combined_text and image_parts:
        log_text = f"{combined_text} [พร้อมรูปภาพ]"

    user_records[uid]["name"] = display_name
    user_records[uid]["count"] += len(msgs)
    user_records[uid]["recent_msgs"].append(log_text)
    room_history.append(f"{display_name}: {log_text}")

    if random.random() < 0.25:
        try:
            reaction_pool = ["💀", "🙄", "😂", "👀", "🤨"]
            await last_message.add_reaction(random.choice(reaction_pool))
        except Exception:
            pass

    room_context = "\n".join(room_history)
    all_users_summary = build_leaderboard_summary()
    current_time = get_thai_time_str()
    need_reply = (channel.last_message_id != last_message.id)

    prompt_text = (
        f"เวลาปัจจุบันในไทย: {current_time}\n"
        f"สมุดจดสถิติและวีรกรรมของทุกคนในห้อง:\n{all_users_summary}\n\n"
        f"แชทล่าสุดในห้อง:\n{room_context}\n\n"
        f"จงตอบกลับ {display_name} แบบคนจริงๆ ทันที (เวลาเรียกชื่อให้สะกดคำว่า {display_name} ตรงตัว ห้ามแปลงเป็นภาษาไทย):"
    )

    contents_payload = [prompt_text] + image_parts if image_parts else prompt_text

    async with channel.typing():
        models_to_try = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]

        for model_name in models_to_try:
            try:
                response = await asyncio.wait_for(
                    client_ai.aio.models.generate_content(
                        model=model_name,
                        contents=contents_payload,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            temperature=0.85,
                        )
                    ),
                    timeout=18.0
                )
                reply_text = (response.text or "").strip()

                if not reply_text:
                    reply_text = f"คำพูดมึงแรงเกินระบบกรองกูรับไม่ได้ว่ะ {display_name} เอาใหม่ดิ๊"

                typing_delay = min(len(reply_text) * 0.025, 2.5)
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
                print(f"Model {model_name} timed out", flush=True)
                continue
            except Exception as e:
                print(f"Model {model_name} failed: {e}", flush=True)
                continue

        await channel.send("สมองค้างแป๊บ คนใช้เยอะ ลองพิมพ์ใหม่อีกทีนะ")

async def idle_chatter_loop():
    tz_thai = timezone(timedelta(hours=7))
    while not bot.is_closed():
        await asyncio.sleep(1800)
        now_utc = datetime.now(timezone.utc)
        now_thai = datetime.now(tz_thai)
        idle_seconds = (now_utc - last_activity_time).total_seconds()

        if idle_seconds > 7200 and 10 <= now_thai.hour <= 23 and random.random() < 0.30:
            channel = bot.get_channel(TARGET_CHANNEL_ID)
            if channel:
                try:
                    response = await asyncio.wait_for(
                        client_ai.aio.models.generate_content(
                            model="gemini-3.5-flash-lite",
                            contents=f"ตอนนี้เวลา {get_thai_time_str()} ห้องแชทเงียบกริบไม่มีใครคุยมา 2 ชั่วโมงแล้ว จงพิมพ์บ่นลอยๆ หรือทักชวนเพื่อนในกลุ่มคุยแบบกวนๆ สั้นๆ 1 ประโยค:",
                            config=types.GenerateContentConfig(
                                system_instruction=SYSTEM_PROMPT,
                                temperature=0.9,
                            )
                        ),
                        timeout=15.0
                    )
                    if response.text:
                        await channel.send(response.text.strip()[:500])
                except Exception:
                    pass

@bot.event
async def on_ready():
    global idle_task_started
    print(f'บอท {bot.user} ออนไลน์พร้อมลุยเต็มระบบแล้ว!', flush=True)
    if not idle_task_started:
        idle_task_started = True
        asyncio.create_task(idle_chatter_loop())

@bot.event
async def on_message(message):
    global last_activity_time
    if message.author.bot:
        return
    if message.channel.id != TARGET_CHANNEL_ID:
        return

    last_activity_time = datetime.now(timezone.utc)
    uid = message.author.id
    pending_messages[uid].append(message)

    if uid in user_tasks and not user_tasks[uid].done():
        user_tasks[uid].cancel()

