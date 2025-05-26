from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from dotenv import load_dotenv
import sys
import os
import openai
from collections import defaultdict
from linebot.models import FlexSendMessage
from linebot.models import QuickReply, QuickReplyButton, MessageAction
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from eeg import process
from gpt_api.response import build_prompt, ask_gpt
from style_selector import make_style_flex
from persona_prompt_map import persona_map

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
user_style = defaultdict(dict)  # 記住每位使用者的三層設定
user_eeg_history = defaultdict(list)
MAX_TURNS = 4  # 最多保留 5 輪對話

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


# === 系統 prompt 對應生成 ===
def build_custom_prompt(style):
    desc = persona_map.get(style.get("persona"), "")
    return (
        "你是一位只會說繁體中文的聊天夥伴，請依照以下角色風格回應使用者："
        + desc +
        "如果近幾輪的聊天內容中有「收到！我會往更...的方向改進！」，請記得以此方向來做修正以符合使用者偏好"
        "\n在日常對話中，根據使用者的輸入與最近幾輪的聊天內容，給出具體、自然、有幫助的回應。\n不要太制式，保持人味，訊息盡量在50字，最後請確認所有回應都是繁體字，回覆不需要用引號括起來"
    )

def make_feedback_quick_reply():
    return QuickReply(
        items=[
            QuickReplyButton(action=MessageAction(label="太長了，請精簡一點", text="太長了，請精簡一點")),
            QuickReplyButton(action=MessageAction(label="太模糊了，請具體一點", text="太模糊了，請具體一點")),
            QuickReplyButton(action=MessageAction(label="太官腔了，請幽默一點", text="太官腔了，請幽默一點")),
        ]
    )

# === 處理使用者訊息 ===
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()
    history = user_eeg_history.get(user_id, [])

    if text == "傳送EEG":
        try:
            # eeg_path = "../data/data_stress.txt"  # 可改為自動讀最新 EEG
            eeg_path = "/mnt/c/Users/陳郁玲/Desktop/BIOPAC/data/data.txt"
            eeg_state = process.predict_prob(eeg_path)
            
            # 加入 EEG 歷史（最多 3 筆）
            user_eeg_history[user_id].append(eeg_state)
            if len(user_eeg_history[user_id]) > 3:
                user_eeg_history[user_id] = user_eeg_history[user_id][-3:]

            # 加入自定義風格，若無則用預設
            style = user_style.get(user_id, {
                "intent": "intent_relax",
                "tone": "tone_soft",
                "persona": "persona_parent"
            })
            
            prompt = build_prompt(eeg_state, history=history)
            print(f"🧠 EEG 分類機率：{eeg_state}")
            reply = ask_gpt(prompt, style)    
            # 建立 EEG 狀態文字描述
            percentages = [f"{prob:.0%}" for prob in eeg_state.values()]
            eeg_text = "🧠 各腦波分類機率：" + f"({', '.join(percentages)})"    

            # 建立 Flex Message
            flex_json = generate_eeg_flex_message(eeg_state)
            flex_msg = FlexSendMessage(alt_text="🧠 腦波狀態分析", contents=flex_json)

            # line_bot_api.push_message(user_id, TextSendMessage(text=reply))
            # line_bot_api.push_message(user_id, flex_msg)
            line_bot_api.reply_message(
                event.reply_token,
                messages=[
                    TextSendMessage(text=reply),
                    TextSendMessage(text=eeg_text),
                    flex_msg
                ]
            )
        except Exception as e:
            # line_bot_api.push_message(user_id, TextSendMessage(text=f"⚠️ 發生錯誤：{e}"))
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"⚠️ 發生錯誤：{e}")
            )

    elif text == "建立專屬角色":
        user_style[user_id] = {}  
        # line_bot_api.push_message(user_id, make_style_flex("persona_only"))
        line_bot_api.reply_message(event.reply_token, make_style_flex("persona_only"))

    elif text.startswith("persona_"):
        user_style[user_id]["persona"] = text
        conversation_history[user_id] = []  # 🔁 清空歷史對話
        # line_bot_api.push_message(user_id, TextSendMessage(text="✅ 已儲存你的對話風格，從現在開始我會照這樣回覆你！"))
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 已儲存你的對話風格，從現在開始我會照這樣回覆你！"))


    else:
        conversation_history[user_id].append({"role": "user", "content": text})
        # 保留最近 MAX_TURNS 輪對話
        if len(conversation_history[user_id]) > MAX_TURNS * 2:
            conversation_history[user_id] = conversation_history[user_id][-MAX_TURNS * 2:]

        style = user_style.get(user_id, {
            "persona": "persona_general"
        })

        system_prompt = build_custom_prompt(style)

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "system", "content": system_prompt}] + conversation_history[user_id]
            )
            reply = response["choices"][0]["message"]["content"]
            conversation_history[user_id].append({"role": "assistant", "content": reply})
            # line_bot_api.push_message(user_id, TextSendMessage(text=reply))
            # ✅ 使用 reply_message 回傳
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=reply,
                    quick_reply=make_feedback_quick_reply()
                )
            )
        except Exception as e:
            # line_bot_api.push_message(user_id, TextSendMessage(text=f"⚠️ GPT 回應錯誤：{e}"))
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"⚠️ GPT 回應錯誤：{e}")
            )



if __name__ == "__main__":
    app.run(port=5000)

