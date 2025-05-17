from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from dotenv import load_dotenv
import sys
import os
import openai
from collections import defaultdict
from linebot.models import FlexSendMessage

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from eeg import process
from gpt.response import build_prompt, ask_gpt

def generate_eeg_flex_message(status_dict):
    # 將輸入的 key 統一轉成標準 label
    label_mapping = {
        "relax": "Relax",
        "concentrating": "Focus",
        "stress": "Stress",
        "memory": "Memory"
    }

    # 狀態對應顏色（需與 label 完全匹配）
    color_map = {
        "Relax": "#5CADAD",   # 青綠色
        "Focus": "#0072E3",   # 紫色
        "Stress": "#FF6B6E",  # 紅色
        "Memory": "#FF8040"   # 綠色
    }

    # 狀態對應短句
    description_map = {
        "Relax": "身心放鬆中",
        "Focus": "專注力集中",
        "Stress": "壓力山大中",
        "Memory": "努力記憶中"
    }

    # 建立單一 bubble
    def make_bubble(label, percent_float, color, description):
        percent_display = round(percent_float * 100, 1)
        percent_str = f"{percent_display}%"
        width_str = f"{percent_display}%"

        return {
            "type": "bubble",
            "size": "nano",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": label,
                        "color": "#ffffff",
                        "align": "start",
                        "size": "md",
                        "gravity": "center"
                    },
                    {
                        "type": "text",
                        "text": percent_str,
                        "color": "#ffffff",
                        "align": "start",
                        "size": "xs",
                        "gravity": "center",
                        "margin": "lg"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [{"type": "filler"}],
                                "width": width_str,
                                "backgroundColor": "#FFFFFF",
                                "height": "6px"
                            }
                        ],
                        "backgroundColor": "#3A3A3A",
                        "height": "6px",
                        "margin": "sm"
                    }
                ],
                "backgroundColor": color,
                "paddingTop": "19px",
                "paddingAll": "12px",
                "paddingBottom": "16px"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": description,
                                "color": "#8C8C8C",
                                "size": "sm",
                                "wrap": True
                            }
                        ],
                        "flex": 1
                    }
                ],
                "spacing": "md",
                "paddingAll": "12px"
            },
            "styles": {
                "footer": {
                    "separator": False
                }
            }
        }

    # 組合所有 bubble
    bubbles = []
    for raw_label, percent_float in status_dict.items():
        label = label_mapping.get(raw_label.lower(), raw_label.title())
        color = color_map.get(label, "#999999")
        desc = description_map.get(label, "Your current brain state")
        bubbles.append(make_bubble(label, percent_float, color, desc))

    return {
        "type": "carousel",
        "contents": bubbles
    }

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
            eeg_path = "../raw_data/S09/6.txt"  # 可改為自動讀最新 EEG
            eeg_state = process.predict_prob(eeg_path)
            prompt = build_prompt(eeg_state)
            print(f"🧠 EEG 分類機率：{eeg_state}")
            reply = ask_gpt(prompt)

            # 建立 Flex Message
            flex_json = generate_eeg_flex_message(eeg_state)
            flex_msg = FlexSendMessage(alt_text="🧠 腦波狀態分析", contents=flex_json)

            line_bot_api.push_message(user_id, TextSendMessage(text=reply))
            line_bot_api.push_message(user_id, flex_msg)
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
                            "你是一位說繁體中文、溫暖幽默又能同理人情緒的聊天夥伴。(必須用繁體中文回答)"
                            "你很會陪伴、安慰和傾聽別人，受眾是大學生，所以你講話可以年輕、有趣，有時候帶點北爛的語氣沒關係。"
                            "在日常對話中，根據使用者的輸入與最近幾輪的聊天內容，給出具體、自然、有幫助的回應。"
                            "不要像機器人一樣講話太制式，可以自然一點、有點人味，甚至偶爾用 emoji 或電機系會懂的詞彙（例如期中爆炸、選課一時爽期末火葬場、哥布林等等）讓人感覺你是真的在陪伴。"
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
