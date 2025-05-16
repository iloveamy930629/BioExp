from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from dotenv import load_dotenv
import sys
import os
import openai
from collections import defaultdict

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from eeg import process
from gpt.response import build_prompt, ask_gpt

# === 初始化 ===
load_dotenv("../.env")
app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# === 對話歷史管理 ===
conversation_history = defaultdict(list)
MAX_TURNS = 6  # 最多保留 5 輪對話

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except Exception as e:
        print(f"⚠️ Webhook 錯誤：{e}")
        abort(400)
    return 'OK'

# === 處理使用者訊息 ===
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()

    if text == "傳送EEG":
        try:
            eeg_path = "../data/S9_1-3.txt"  # 可改為自動讀最新 EEG
            eeg_state = process.predict_prob(eeg_path)
            prompt = build_prompt(eeg_state)
            reply = ask_gpt(prompt)
            line_bot_api.push_message(user_id, TextSendMessage(text=reply))
        except Exception as e:
            line_bot_api.push_message(user_id, TextSendMessage(text=f"⚠️ 發生錯誤：{e}"))

    elif text == "重設對話":
        conversation_history[user_id] = []
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 對話已重置。"))

    else:
        conversation_history[user_id].append({"role": "user", "content": text})
        # 保留最近 MAX_TURNS 輪對話
        if len(conversation_history[user_id]) > MAX_TURNS * 2:
            conversation_history[user_id] = conversation_history[user_id][-MAX_TURNS * 2:]

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是一位溫柔且聰明的聊天夥伴，擅長傾聽、陪伴與提供協助。"
                            "你可以討論日常生活、學習、壓力、目標、實驗、創意點子等等。"
                            "請根據使用者的輸入與先前的對話內容給出具體、有幫助且自然的回應。"
                        )
                    }
                ] + conversation_history[user_id]
            )
            reply = response["choices"][0]["message"]["content"]
            conversation_history[user_id].append({"role": "assistant", "content": reply})
            line_bot_api.push_message(user_id, TextSendMessage(text=reply))
        except Exception as e:
            line_bot_api.push_message(user_id, TextSendMessage(text=f"⚠️ GPT 回應錯誤：{e}"))

if __name__ == "__main__":
    app.run(port=5000)
