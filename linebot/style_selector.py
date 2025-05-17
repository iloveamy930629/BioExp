# 📁 linebot/style_selector.py

from linebot.models import FlexSendMessage

# === 預設每層選項內容（你可擴充或調整） ===
STYLE_LAYERS = {
    "layer1": {
        "title": "你現在需要哪一種陪伴？",
        "options": [
            ("🛏 放鬆陪伴", "intent_relax", "我只是想要輕鬆一下、被安慰、耍廢一下"),
            ("🧠 認真建議", "intent_advice", "我想要明確、有用的建議，實際解決問題"),
            ("🪞 被理解", "intent_empathy", "我希望有人能聽懂我的處境或情緒"),
            ("🎭 被激勵", "intent_motivate", "我需要被激起幹勁或打醒"),
            ("👂 想發洩", "intent_vent", "我只想說話，有人聽我講就好")
        ]
    },
    "layer2": {
        "title": "你喜歡什麼樣的語氣？",
        "options": [
            ("🧸 溫柔體貼", "tone_soft", "像抱枕，溫暖療癒、陪你慢慢說"),
            ("🤣 嘴砲幽默", "tone_funny", "會講幹話，但其實有用，讓你笑一下"),
            ("🧠 務實條列", "tone_practical", "清楚條列，重點整理、目標導向"),
            ("😎 酷帥冷靜", "tone_cool", "講話不多，但有 punch、有型"),
            ("😈 毒舌鬧你", "tone_roast", "故意嘴你一波，但內心其實關心你")
        ]
    },
    "layer3": {
        "title": "你想對話的角色是誰？",
        "options": [
            ("👩‍🎓 學長姐型", "persona_senior", "親切但可能有點毒，講話有個性，像過來人傳承經驗"),
            ("👽 外星觀察員型", "persona_alien", "講話超脫、不合常理，卻時不時講出哲學金句，讓人豁然開朗"),
            ("👦 小廢柴同學型", "persona_slacker", "廢但懂你，語氣鬆散，會自嘲，一起爛但偶爾講出正經建議"),
            ("👩‍🏫 老師父母型", "persona_parent", "比較嚴肅成熟，會提醒你自己應該怎麼做，語氣關心但不寵溺"),
            ("💑 男/女朋友型", "persona_lover", "給你很多情緒價值、讚美與關愛，像在抱你說你值得被愛")
        ]
    }
}

# === 建立 flex message ===
def make_style_flex(layer_key):
    layer = STYLE_LAYERS[layer_key]
    bubbles = []
    for label, value, desc in layer["options"]:
        bubble = {
            "type": "bubble",
            "size": "mega",
            "hero": {
                "type": "image",
                "url": "https://scdn.line-apps.com/n/channel_devcenter/img/fx/01_1_cafe.png",
                "size": "full",
                "aspectRatio": "20:13",
                "aspectMode": "cover"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {"type": "text", "text": label, "weight": "bold", "size": "xl", "wrap": True},
                    {"type": "text", "text": desc, "size": "sm", "wrap": True, "color": "#666666"}
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "action": {
                            "type": "message",
                            "label": "就是這個！",
                            "text": value
                        }
                    }
                ]
            }
        }
        bubbles.append(bubble)
    return FlexSendMessage(alt_text="請選擇風格", contents={"type": "carousel", "contents": bubbles})