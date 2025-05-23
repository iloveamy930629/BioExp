import os
import openai
from dotenv import load_dotenv
from gpt.persona_map import persona_map

load_dotenv("../.env")
openai.api_key = os.getenv("OPENAI_API_KEY")

def build_prompt(eeg_state, history=None):
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
    
    # 加入歷史紀錄
    history_summary = ""
    if history and len(history) > 1:
        recent = []
        for hist in history[-3:]:
            dominant = max(hist.items(), key=lambda x: x[1])[0]
            recent.append(label_map.get(dominant, dominant))
        history_summary = (
            f"\n（歷史資料：{' → '.join(recent)}）"
        )

    # 結構化 prompt
    prompt = (
        f"請依據以下腦波狀態：{state_str}，其中主要狀態為「{dominant_label}（{percent_text}）」。"
        + history_summary +
        f"請生成一段包含以下格式的文字：\n\n"
        f"🎯 目前狀態：{dominant_label}（{percent_text}）\n\n"
        f"📈 狀態變化:閱讀歷史資料，直接用「記憶 → 放鬆 → 記憶」類似這樣的方式呈現狀態變化，沒有歷史資料時則不生成狀態變化這一行\n\n"
        f"🧠 分析：一句話說明這種狀態通常會有什麼感受或現象（用年輕語氣、100字以內）\n\n"
        f"🌱 建議與鼓勵：一段建議或安慰的話，符合角色設定(150字以內)\n\n"
    )
    print("=== 最終生成的 Prompt ===")
    print(prompt)

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

        # 根據角色風格整合風格描述
        persona_desc = ""
        if style and "persona" in style:
            persona_key = style.get("persona")
            persona_desc = persona_map.get(persona_key, "")

        full_system_prompt = base_system_prompt + "\n\n" + persona_desc

        # 建立對話
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": full_system_prompt},
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