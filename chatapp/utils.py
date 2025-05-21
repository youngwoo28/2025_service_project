# utils/history_saver.py

import os
import json
from datetime import datetime

HISTORY_DIR = "history"

def save_emotion_history(chat_log, emotion_history):
    if not os.path.exists(HISTORY_DIR):
        os.makedirs(HISTORY_DIR)

    today = datetime.now().strftime("%Y-%m-%d")
    file_path = os.path.join(HISTORY_DIR, f"{today}.json")

    data = {
        "date": today,
        "chat_log": chat_log,
        "emotion_history": emotion_history
    }

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"📁 감정 히스토리 저장 완료: {file_path}")
