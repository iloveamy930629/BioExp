import os
import openai
from dotenv import load_dotenv

load_dotenv("../.env")
openai.api_key = os.getenv("OPENAI_API_KEY")


def build_prompt(eeg_state):
    """
    根據 EEG 分類機率輸出適合 GPT 的提示語句。
    eeg_state: Dict，例如 {'relax': 0.2, 'concentrating': 0.3, 'stress': 0.4, 'memory': 0.1}
    """
    sorted_state = sorted(eeg_state.items(), key=lambda x: x[1], reverse=True)
    state_text = "，".join([f"{k} {int(v * 100)}%" for k, v in sorted_state])
    prompt = f"你是一個溫柔的聊天夥伴，對方的腦波狀態如下：{state_text}，請用100字鼓勵他。"
    return prompt

# 載入 API 金鑰
def ask_gpt(prompt):
    """
    呼叫 OpenAI GPT API，輸入 prompt，回傳回應文字。
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "你是一個能根據腦波數據安慰或鼓勵用戶的聊天機器人。"},
                {"role": "user", "content": prompt}
            ]
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        return f"⚠️ GPT 呼叫失敗：{e}"

# 測試用
# eeg_state = {'relax': 0.2, 'concentrating': 0.3, 'stress': 0.4, 'memory': 0.1}
# prompt = build_prompt(eeg_state)
# reply = ask_gpt(prompt)
# print(reply)