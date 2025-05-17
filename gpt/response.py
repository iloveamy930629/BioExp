import os
import openai
from dotenv import load_dotenv

load_dotenv("../.env")
openai.api_key = os.getenv("OPENAI_API_KEY")

def build_prompt(eeg_state):
    """
    根據 EEG 分類機率輸出適合 GPT 的提示語句，讓 GPT 以年輕幽默又專業的方式回應。
    """
    # 中文轉換對應
    label_map = {
        "relax": "放鬆",
        "concentrating": "專注",
        "stress": "壓力",
        "memory": "記憶"
    }

    # 強化主導狀態的區分（拉大比例差異）
    amplified = {k: v ** 1.5 for k, v in eeg_state.items()}
    total = sum(amplified.values())
    normed = {k: v / total for k, v in amplified.items()}

    # 取主導狀態
    sorted_state = sorted(normed.items(), key=lambda x: x[1], reverse=True)
    dominant_key, dominant_val = sorted_state[0]
    dominant_label = label_map[dominant_key]
    # 但 percent_text 改為原始值
    true_percent = eeg_state[dominant_key]
    percent_text = f"{round(true_percent * 100, 1)}%"

    # 完整狀態描述
    state_str = "，".join([f"{label_map[k]} {round(v * 100, 1)}%" for k, v in sorted_state])

    # 結構化 prompt
    prompt = (
        f"請依據以下腦波狀態：{state_str}，其中主要狀態為「{dominant_label}（{percent_text}）」。"
        f"請生成一段包含以下格式的文字：\n\n"
        f"🎯 目前狀態：{dominant_label}（{percent_text}）\n\n"
        f"🧠 分析：一句話說明這種狀態會有什麼感受或現象（用年輕語氣、100字以內）\n\n"
        f"🌱 建議與鼓勵：一段有實際幫助的建議，生活化一點(150字以內)\n\n"
    )
    return prompt

# def ask_gpt(prompt, style=None):
#     try:
#         response = openai.ChatCompletion.create(
#             model="gpt-4",
#             messages=[
#                 {
#                     "role": "system",
#                     "content": (
#                         "你是一位會說繁體中文、懂腦波、懂電機系大學生的陪聊夥伴。"
#                         "你很會安慰、理解別人心理狀態，用詞自然不做作，有時候可以輕鬆幽默，"
#                         "但重點是讓對方覺得被理解、有幫助。請根據 prompt 分析出對方的主導狀態並給出專業但貼近生活的建議。"
#                     )
#                 },
#                 {"role": "user", "content": prompt}
#             ]
#         )
#         return response['choices'][0]['message']['content']
#     except Exception as e:
#         return f"⚠️ GPT 呼叫失敗：{e}"

def ask_gpt(prompt, style=None):
    try:
        # 預設的角色描述
        base_system_prompt = (
            "你是一位會說繁體中文、懂腦波、理解別人心理狀態、用詞自然不做作。"
            "你擅長安慰、鼓勵、或陪伴電機系大學生，回應風格要有溫度、自然，必要時可以年輕幽默。"
        )

        # 若有 style，整合補充說明
        if style:
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
                "persona_parent": "像爸媽老師，比較嚴肅成熟，會「提醒對方應該怎麼做」，語氣關心但不寵溺",
                "persona_lover": "像戀人，給很多情緒價值、讚美與關愛，講話像抱、撫摸、肯定對方"
            }
            additions = [
                intent_map.get(style.get("intent"), ""),
                tone_map.get(style.get("tone"), ""),
                persona_map.get(style.get("persona"), "")
            ]
            additions = [s for s in additions if s]
            style_str = "風格設定為：" + "；".join(additions) if additions else ""
            full_prompt = base_system_prompt + (f"\n{style_str}" if style_str else "")
        else:
            full_prompt = base_system_prompt

        # 建立對話
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": full_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        return f"⚠️ GPT 呼叫失敗：{e}"

# def build_prompt(eeg_state):
#     """
#     根據 EEG 分類機率輸出適合 GPT 的提示語句。
#     eeg_state: Dict，例如 {'relax': 0.2, 'concentrating': 0.3, 'stress': 0.4, 'memory': 0.1}
#     """
#     sorted_state = sorted(eeg_state.items(), key=lambda x: x[1], reverse=True)
#     state_text = "，".join([f"{k} {int(v * 100)}%" for k, v in sorted_state])
#     prompt = f"你是一個溫柔的聊天夥伴，對方的腦波狀態如下：{state_text}，請用100字鼓勵他。"
#     return prompt

# 載入 API 金鑰
# def ask_gpt(prompt):
#     """
#     呼叫 OpenAI GPT API，輸入 prompt，回傳回應文字。
#     """
#     try:
#         response = openai.ChatCompletion.create(
#             model="gpt-4",
#             messages=[
#                 {"role": "system", "content": "你是一個能根據腦波數據安慰或鼓勵用戶的聊天機器人。"},
#                 {"role": "user", "content": prompt}
#             ]
#         )
#         return response['choices'][0]['message']['content']
#     except Exception as e:
#         return f"⚠️ GPT 呼叫失敗：{e}"

# 測試用
# eeg_state = {'relax': 0.2, 'concentrating': 0.3, 'stress': 0.4, 'memory': 0.1}
# prompt = build_prompt(eeg_state)
# reply = ask_gpt(prompt)
# print(reply)