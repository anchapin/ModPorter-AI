#!/usr/bin/env python3
import os
import json
import httpx
import random

output_path = "/home/alex/Projects/portkit/ai_engine/mmsd/data/raw/instructions.jsonl"
os.makedirs(os.path.dirname(output_path), exist_ok=True)

themes = [
    "Industrial Automation", "Advanced Sorcery", "Farming", "Transportation",
    "Quality of Life", "Mob Overhaul", "Medieval Weapons", "Space Exploration",
    "Deep Sea", "Cybernetic", "Ecosystem", "Economic", "Storage",
    "Furniture", "Weather", "Combat", "Pets", "Archaeology", "Underground", "Music"
]

model = "llama3.2:latest"
url = "http://localhost:11434/api/generate"

count = 0
print(f"Starting generation to reach 1400 instructions...")

while count < 1400:
    theme = random.choice(themes)
    try:
        resp = httpx.post(url, json={
            "model": model,
            "prompt": f"Minecraft mod: {theme}",
            "system": "Creative mod idea",
            "stream": False,
            "options": {"temperature": 0.9}
        }, timeout=20.0)
        if resp.status_code == 200:
            txt = resp.json().get("response", "").strip()
            if txt:
                with open(output_path, "a") as f:
                    f.write(json.dumps({"instruction": txt}) + "\n")
                count += 1
                print(f"[{count}/1400] {txt[:50]}...")
    except Exception as e:
        print(f"Error: {e}")

print(f"DONE! Total: {count}")
