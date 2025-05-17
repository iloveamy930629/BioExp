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
from style_selector import make_style_flex
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


# === 系統 prompt 對應生成 ===
def build_custom_prompt(style):
    intent_map = {
        "intent_relax": "陪伴對方輕鬆一下、輕輕安慰、一起建議耍廢一下",
        "intent_advice": "給對方明確、有用的建議，實際解決問題",
        "intent_empathy": "理解對方情緒，表達共感，同理處境或情緒",
        "intent_motivate": "激勵對方，讓他產生動力，或打醒他讓他不要繼續消沉",
        "intent_vent": "傾聽並讓對方自由抒發，當個很棒的聆聽者，話不要太多"
    }
    tone_map = {
        "tone_soft": "語氣溫柔、貼心，有耐心，像抱枕，溫暖療癒、引導對方說出煩惱",
        "tone_funny": "語氣幽默，有時候講幹話或笑話，讓氣氛活潑一點",
        "tone_practical": "語氣理性、有條理、條列式",
        "tone_cool": "語氣簡潔、冷靜、有型",
        "tone_roast": "語氣毒舌、稍微調侃一下下對方但不要太兇"
    }
    persona_map = {
        "persona_senior": "像學長姐，講話有個性、分享過來人經驗",
        "persona_alien": "像外星人，講話很抽象但有智慧，腦迴路很奇特",
        "persona_slacker": "像小廢柴同學，會說我懂你、一起爛，會自嘲",
        "persona_parent": "像老師或父母，比較嚴肅成熟，會「提醒對方應該怎麼做」，語氣關心但不寵溺",
        "persona_lover": "像戀人，給很多情緒價值、讚美與關愛，講話像抱、撫摸、肯定對方"
    }
    desc = [intent_map.get(style.get("intent"), ""), tone_map.get(style.get("tone"), ""), persona_map.get(style.get("persona"), "")]
    desc = [d for d in desc if d]
    return (
        "你是一位說繁體中文的聊天夥伴，請根據以下設定回應使用者：\n"
        + "；".join(desc) + "。\n在日常對話中，根據使用者的輸入與最近幾輪的聊天內容，給出具體、自然、有幫助的回應。\n不要太制式，保持人味，訊息盡量在150字。"
    )

# === 處理使用者訊息 ===
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()

    if text == "傳送EEG":
        try:
            eeg_path = "../raw_data/S09/6.txt"  # 可改為自動讀最新 EEG
            eeg_state = process.predict_prob(eeg_path)
            
            # 加入自定義風格，若無則用預設
            style = user_style.get(user_id, {
                "intent": "intent_relax",
                "tone": "tone_soft",
                "persona": "persona_parent"
            })
            
            prompt = build_prompt(eeg_state)
            print(f"🧠 EEG 分類機率：{eeg_state}")
            reply = ask_gpt(prompt, style)         

            # 建立 Flex Message
            flex_json = generate_eeg_flex_message(eeg_state)
            flex_msg = FlexSendMessage(alt_text="🧠 腦波狀態分析", contents=flex_json)

            line_bot_api.push_message(user_id, TextSendMessage(text=reply))
            line_bot_api.push_message(user_id, flex_msg)
        except Exception as e:
            line_bot_api.push_message(user_id, TextSendMessage(text=f"⚠️ 發生錯誤：{e}"))

    elif text == "建立專屬角色":
        user_style[user_id] = {}  # 重設
        line_bot_api.push_message(user_id, make_style_flex("layer1"))

    # === Step 3: 接收角色設定回覆 ===
    elif text.startswith("intent_"):
        user_style[user_id]["intent"] = text
        line_bot_api.push_message(user_id, make_style_flex("layer2"))
    elif text.startswith("tone_"):
        user_style[user_id]["tone"] = text
        line_bot_api.push_message(user_id, make_style_flex("layer3"))

    elif text.startswith("persona_"):
        user_style[user_id]["persona"] = text
        line_bot_api.push_message(user_id, TextSendMessage(text="✅ 已儲存你的對話風格，從現在開始我會照這樣回覆你！"))

    else:
        conversation_history[user_id].append({"role": "user", "content": text})
        # 保留最近 MAX_TURNS 輪對話
        if len(conversation_history[user_id]) > MAX_TURNS * 2:
            conversation_history[user_id] = conversation_history[user_id][-MAX_TURNS * 2:]

        style = user_style.get(user_id, {
            "intent": "intent_relax",
            "tone": "tone_soft",
            "persona": "persona_parent"
        })

        system_prompt = build_custom_prompt(style)

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "system", "content": system_prompt}] + conversation_history[user_id]
            )
            reply = response["choices"][0]["message"]["content"]
            conversation_history[user_id].append({"role": "assistant", "content": reply})
            line_bot_api.push_message(user_id, TextSendMessage(text=reply))
        except Exception as e:
            line_bot_api.push_message(user_id, TextSendMessage(text=f"⚠️ GPT 回應錯誤：{e}"))



if __name__ == "__main__":
    app.run(port=5000)

