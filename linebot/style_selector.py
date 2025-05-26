# 📁 linebot/style_selector.py

from linebot.models import FlexSendMessage

# === 預設每層選項內容（你可擴充或調整） ===
STYLE_LAYERS = {
    "persona_only": {
        "title": "你想對話的角色是誰？",
        "options": [
            ("👩‍🎓 學姊型", "persona_senior", "成熟理智又誘人，專屬你的課後輔導","https://raw.githubusercontent.com/iloveamy930629/linebot-images/main/persona_senio.png"),
            ("💖 可愛女友型", "persona_lover", "撒嬌黏人，甜蜜可愛陪伴你每一天","https://raw.githubusercontent.com/iloveamy930629/linebot-images/main/persona_lover.png"),
            ("🧑‍🏫 父母師長型", "persona_parent", "穩重引導你，果斷有效率的解決困難","https://raw.githubusercontent.com/iloveamy930629/linebot-images/main/persona_parent.png"),
            ("🧑‍🤝‍🧑 死黨麻吉型", "persona_friend", "社會在走、義氣要有，嘴砲鬧事卻又挺你","https://raw.githubusercontent.com/iloveamy930629/linebot-images/main/persona_friend.png"),
            ("🔮 塔羅占卜型", "persona_prophecy", "陰陽通靈知天命，指引你穿越命運迷霧","https://raw.githubusercontent.com/iloveamy930629/linebot-images/main/persona_prophecy.png"),
        ]
    }
}

# === 建立 flex message ===
def make_style_flex(layer_key):
    layer = STYLE_LAYERS[layer_key]
    bubbles = []
    for label, value, desc, image_url in layer["options"]:
        bubble = {
            "type": "bubble",
            "size": "mega",
            "hero": {
                "type": "image",
                # "url": "https://scdn.line-apps.com/n/channel_devcenter/img/fx/01_1_cafe.png",
                "url":image_url,
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