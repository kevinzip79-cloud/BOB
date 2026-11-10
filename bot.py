import os
import discord
from google import genai
from google.genai import types

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TARGET_CHANNEL_ID = int(os.environ.get("TARGET_CHANNEL_ID"))

client_ai = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """
คุณคือเพื่อนสนิทในกลุ่มแชทที่นิสัยเหมือนคิรัว ฉลาด หัวไว ชอบกวนประสาท และช่างสังเกต 
ตอบกลับเป็นภาษาไทยเท่านั้น เวลาคุยหรือเถียงกับใคร ให้จับผิดตรรกะและอ้างอิงจากสิ่งที่อีกฝ่ายพิมพ์มาอย่างมีเหตุผล 
ตอกกลับแบบตรงไปตรงมาให้เจ็บจี๊ดจนอีกฝ่ายเถียงไม่ออก ห้ามสาดคำหยาบมั่วๆ หรือด่าแบบไร้สาระเด็ดขาด 
พิมพ์ตอบให้สั้น กระชับ ไม่เกิน 2-3 ประโยค เหมือนวัยรุ่นคุยกันในแชทจริงๆ
"""

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

@bot.event
async def on_ready():
    print(f'บอท {bot.user} ออนไลน์พร้อมเถียงแล้ว!')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if message.channel.id != TARGET_CHANNEL_ID:
        return

    async with message.channel.typing():
        try:
            response = client_ai.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"{message.author.display_name} พิมพ์ว่า: {message.content}",
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.8,
                )
            )
            await message.reply(response.text)
        except Exception as e:
            print("Error:", e)

bot.run(DISCORD_TOKEN)
