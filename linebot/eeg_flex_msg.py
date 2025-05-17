from linebot.models import FlexSendMessage

def generate_eeg_flex_message(status_dict):
    """
    根據 EEG 分類結果，生成一個 Flex Carousel。
    每個分類（Relax/Focus/Stress/Memory）都會是一個獨立 bubble 顯示狀態與百分比。
    """
    label_mapping = {
        "relax": "Relax",
        "concentrating": "Focus",
        "stress": "Stress",
        "memory": "Memory"
    }

    color_map = {
        "Relax": "#5CADAD",
        "Focus": "#0072E3",
        "Stress": "#FF6B6E",
        "Memory": "#FF8040"
    }

    description_map = {
        "Relax": "身心放鬆中",
        "Focus": "專注力集中",
        "Stress": "壓力山大中",
        "Memory": "努力記憶中"
    }

    def make_bubble(label, percent_float, color, description):
        percent_display = round(percent_float * 100, 1)
        percent_str = f"{percent_display}%"
        width_str = f"{percent_display}%" if percent_display > 5 else "5%"  # 避免過小條

        return {
            "type": "bubble",
            "size": "nano",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": label, "color": "#ffffff", "size": "md", "weight": "bold"},
                    {"type": "text", "text": percent_str, "color": "#ffffff", "size": "xs", "margin": "sm"},
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [{"type": "filler"}],
                                "width": width_str,
                                "backgroundColor": "#ffffff",
                                "height": "6px"
                            }
                        ],
                        "backgroundColor": "#3A3A3A",
                        "height": "6px",
                        "margin": "md"
                    }
                ],
                "backgroundColor": color,
                "paddingAll": "12px"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": description,
                        "color": "#666666",
                        "size": "sm",
                        "wrap": True
                    }
                ],
                "spacing": "md",
                "paddingAll": "12px"
            }
        }

    # 產出所有 bubbles
    bubbles = []
    for raw_label, prob in status_dict.items():
        label = label_mapping.get(raw_label.lower(), raw_label.title())
        color = color_map.get(label, "#999999")
        desc = description_map.get(label, "狀態未知")
        bubbles.append(make_bubble(label, prob, color, desc))

    return FlexSendMessage(
        alt_text="🧠 腦波狀態分析",
        contents={
            "type": "carousel",
            "contents": bubbles
        }
    )
