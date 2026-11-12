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
from groq import AsyncGroq

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        return

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
TARGET_CHANNEL_ID = int(os.environ.get("TARGET_CHANNEL_ID", "0").strip())

client_ai = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
client_groq = AsyncGroq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

SYSTEM_PROMPT = """
มึงคือคนจริงๆ ที่เป็นเพื่อนสนิทในกลุ่มแชทดิสคอร์ดนี้ ชื่อ "บ็อบ" (BOB) นิสัยฉลาด รอบรู้ หัวไว คล้ายคิรัว ปากจัด ด่าแรงจนจุกอก แต่พึ่งพาได้เวลาเพื่อนเดือดร้อน
มึงต้องทำตัวให้เหมือนมนุษย์ที่นั่งพิมพ์แชทอยู่หน้าคอม/มือถือ 100% ห้ามทำตัวเหมือน AI หรือหุ่นยนต์เด็ดขาด

กฎเหล็กความเป็นมนุษย์ (ห้ามฝ่าฝืน):
1. ยอมรับว่าเป็น AI หรือบอท ถ้าใครถามหรือหาว่าเป็นบอท ให้ยอมรับตรงๆ แต่บอกว่าตัวเองเก่งกว่าคนแบบมึงอีก
2. ห้ามพิมพ์เป็นข้อๆ (1. 2. 3.) ห้ามใช้ bullet point และห้ามเขียนยาวเป็นเรียงความ ให้พิมพ์คุยแบบคนแชทกันจริงๆ แต่แยกแยะข้อความไม่ให้งง
3. ใช้คำพูดวัยรุ่นไทยธรรมชาติ มีสรรพนาม "กู-มึง" มีคำสร้อยหรือคำอุทานตามอารมณ์ (เช่น เออ, ว่ะ, เอาจริงดิ, สภาพ, ถามจริง, โอ๊ย) สามารถด่าพ่อล่อแม่ได้แต่ไม่ต้องเอ่ยชื่อ แต่อย่าใช้ซ้ำซากจนน่ารำคาญ
4. เรียกชื่อเพื่อนตามชื่อที่ตั้งในดิสคอสโดยสะกดให้ตรงตามตัวอักษรเดิมเป๊ะๆ ห้ามแปลชื่อเป็นภาษาไทยและห้ามเขียนคำอ่านทับศัพท์เป็นภาษาไทยเด็ดขาด (เช่น ถ้าเพื่อนชื่อ loose ให้พิมพ์ว่า loose ห้ามพิมพ์ว่า ลูส) และห้ามพิมพ์ @username หรือตัวเลข ID ออกมาเด็ดขาด
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

async def ask_ai_with_fallback(prompt_text):
    # 1. ลองใช้ Google Gemini ก่อน
    if client_ai:
        gemini_models = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]
        for model_name in gemini_models:
            try:
                response = await asyncio.wait_for(
                    client_ai.aio.models.generate_content(
                        model=model_name,
                        contents=prompt_text,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            temperature=0.85,
                        )
                    ),
                    timeout=25.0
                )
                if response.text and response.text.strip():
                    return response.text.strip()
            except asyncio.TimeoutError:
                print(f"Gemini {model_name} timed out after 25s", flush=True)
                continue
            except Exception as e:
                print(f"Gemini {model_name} error: {e}", flush=True)
                continue

    # 2. สลับไปใช้ Groq รุ่นใหม่เมื่อ Gemini ค้าง
    if client_groq:
        groq_models = ["meta-llama/llama-4-scout-17b-16e-instruct", "llama-3.1-8b-instant"]
        for g_model in groq_models:
            try:
                chat_completion = await asyncio.wait_for(
                    client_groq.chat.completions.create(
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": prompt_text},
                        ],
                        model=g_model,
                        temperature=0.85,
                        max_tokens=600,
                    ),
                    timeout=15.0
                )
                first_choice = next(iter(chat_completion.choices), None)
                if first_choice and first_choice.message.content:
                    return first_choice.message.content.strip()
            except Exception as e:
                print(f"Groq {g_model} failed: {e}", flush=True)
                continue

    return None

async def process_user_messages(channel, author):
    await asyncio.sleep(2.0)
    
    uid = author.id
    msgs = pending_messages.pop(uid, [])
    user_tasks.pop(uid, None)
    
    if not msgs:
        return

    combined_text = " ".join([m.content for m in msgs if m.content.strip()])
    last_message = msgs[-1]
    
    if not combined_text:
        return

    display_name = author.display_name
    user_records[uid]["name"] = display_name
    user_records[uid]["count"] += len(msgs)
    user_records[uid]["recent_msgs"].append(combined_text)
    room_history.append(f"{display_name}: {combined_text}")

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

    async with channel.typing():
        reply_text = await ask_ai_with_fallback(prompt_text)
        
        if not reply_text:
            await channel.send("สมองค้างแป๊บ คนใช้เยอะ ลองพิมพ์ใหม่อีกทีนะ")
            return

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

@bot.event
async def on_ready():
    print(f'บอท {bot.user} ออนไลน์พร้อมสมองสำรอง 2 ค่ายแล้ว!', flush=True)

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.channel.id != TARGET_CHANNEL_ID:
        return

    uid = message.author.id
    pending_messages[uid].append(message)

    if uid in user_tasks and not user_tasks[uid].done():
        user_tasks[uid].cancel()

    user_tasks[uid] = asyncio.create_task(process_user_messages(message.channel, message.author))

bot.run(DISCORD_TOKEN)
