import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from google import genai
from google.genai import types

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

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
คุณคือเพื่อนสนิทในกลุ่มแชทที่นิสัยเหมือนคิรัว ฉลาด หัวไว ชอบกวนประสาท และช่างสังเกต 
ตอบกลับเป็นภาษาไทยเท่านั้น เวลาคุยหรือเถียงกับใคร ให้จับผิดตรรกะและอ้างอิงจากสิ่งที่อีกฝ่ายพิมพ์มาอย่างมีเหตุผล 
ตอกกลับแบบตรงไปตรงมาให้เจ็บจี๊ดจนอีกฝ่ายเถียงไม่ออก ห้ามสาดคำหยาบมั่วๆ หรือด่าแบบไร้สาระเด็ดขาด 
พิมพ์ตอบให้สั้น กระชับ ไม่เกิน 2 ประโยค เหมือนวัยรุ่นคุยกันในแชทจริงๆ
"""

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

@bot.event
async def on_ready():
    print(f'บอท {bot.user} ออนไลน์พร้อมเถียงแล้ว!', flush=True)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if message.channel.id != TARGET_CHANNEL_ID:
        return

    async with message.channel.typing():
        try:
            response = client_ai.models.generate_content(
                model="gemini-3.8-flash",
                contents=f"{message.author.display_name} พิมพ์ว่า: {message.content}",
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.8,
                )
            )
            reply_text = response.text or "คิดไม่ออกแฮะ"
            await message.channel.send(reply_text[:1900])
        except Exception as e:
            print("Error:", e, flush=True)
            try:
                await message.channel.send(f"ระบบขัดข้อง: {str(e)[:1500]}")
            except Exception as send_err:
                print("Send Error:", send_err, flush=True)

bot.run(DISCORD_TOKEN)
