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
        f"你是一個專業又會說繁體中文的聊天夥伴，擅長分析腦波並安慰或鼓勵台灣的大學生。"
        f"請依據以下腦波狀態：{state_str}，其中主要狀態為「{dominant_label}（{percent_text}）」。"
        f"請生成一段包含以下格式的文字：\n\n"
        f"🎯 目前主導狀態：{dominant_label}（{percent_text}）\n\n"
        f"🧠 分析：一句話說明這種狀態會有什麼感受或現象（用年輕語氣）\n\n"
        f"🌱 建議：一段有實際幫助的建議，生活化一點\n\n"
        f"🔥 加油：一句有趣又真誠的鼓勵話語，可以加入 emoji，不能太浮誇"
    )
    return prompt
def ask_gpt(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是一位會說繁體中文、懂腦波、懂電機系大學生的陪聊夥伴。"
                        "你很會安慰、理解別人心理狀態，用詞自然不做作，有時候可以輕鬆幽默，"
                        "但重點是讓對方覺得被理解、有幫助。請根據 prompt 分析出對方的主導狀態並給出專業但貼近生活的建議。"
                    )
                },
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