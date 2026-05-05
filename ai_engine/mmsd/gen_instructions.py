#!/usr/bin/env python3
import os
import json
import httpx
import random
import asyncio

output_path = "/home/alex/mmsd-work/data/raw/instructions.jsonl"
os.makedirs(os.path.dirname(output_path), exist_ok=True)

themes = [
    "Industrial Automation", "Advanced Sorcery", "Farming", "Transportation",
    "Quality of Life", "Mob Overhaul", "Medieval Weapons", "Space Exploration",
    "Deep Sea", "Cybernetic", "Ecosystem", "Economic", "Storage",
    "Furniture", "Weather", "Combat", "Pets", "Archaeology", "Underground", "Music"
]

url = "http://localhost:8001/v1/chat/completions"

SYSTEM_PROMPT = """You generate Minecraft mod concepts. Output ONLY the mod idea in 2-4 sentences. Format: Title on first line, then brief description. No preamble, no disclaimers, no markdown. Example:

Portable Campfire Mod
Adds craftable campfire items that can be carried in inventory and placed anywhere. They provide warmth in cold biomes and cook food slowly when nearby."""

USER_TEMPLATE = "Create a unique Minecraft mod concept in the '{theme}' category. Be specific about mechanics and features. 2-4 sentences only."

def count_existing():
    if not os.path.exists(output_path):
        return 0
    with open(output_path, "r") as f:
        return sum(1 for _ in f)

def is_valid(text):
    if not text or len(text) < 20:
        return False
    lower = text.lower()
    banned = ["as an ai", "i cannot", "language model", "i can't", "i'm not able", "sorry, i"]
    return not any(b in lower for b in banned)

async def generate_one(client, theme):
    try:
        resp = await client.post(url, json={
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_TEMPLATE.format(theme=theme)}
            ],
            "temperature": 1.0,
            "max_tokens": 512
        }, timeout=120.0)
        if resp.status_code == 200:
            txt = resp.json()["choices"][0]["message"]["content"].strip()
            if is_valid(txt):
                return txt
    except Exception:
        pass
    return None

async def run_parallel(concurrency=4):
    count = count_existing()
    target = 1400
    print(f"Starting parallel generation ({concurrency} concurrent). Have {count}, need {target}.")

    semaphore = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient() as client:
        while count < target:
            batch_size = min(concurrency * 4, target - count)
            tasks = []
            themes_batch = [random.choice(themes) for _ in range(batch_size)]

            async def guarded(theme):
                async with semaphore:
                    return await generate_one(client, theme)

            for theme in themes_batch:
                tasks.append(guarded(theme))

            results = await asyncio.gather(*tasks)

            with open(output_path, "a") as f:
                for text in results:
                    if text:
                        f.write(json.dumps({"instruction": text}) + "\n")
                        count += 1

            print(f"[{count}/{target}] Batch done. Rate: {batch_size} requested, {sum(1 for r in results if r)} valid.")

    print(f"DONE! Total: {count}")

if __name__ == "__main__":
    asyncio.run(run_parallel(concurrency=4))
