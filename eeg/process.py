import numpy as np
import torch
import torch.nn as nn
import torch
import joblib

# === 特徵提取 ===
def extract_band_power(vec, freqs):
    bands = {
        "delta": (0.5, 4),
        "theta": (4, 8),
        "alpha": (8, 13),
        "low-beta": (13, 20),
        "high-beta": (20,30),
        "gamma": (30, 50)
    }
    powers = []
    for (low, high) in bands.values():
        idx = np.where((freqs >= low) & (freqs < high))
        powers.append(np.mean(vec[idx]))
    return np.array(powers)

def extract_features(vec):
    vec_safe = vec + 1e-8
    return np.array([
        np.mean(vec),
        np.std(vec),
        np.sqrt(np.mean(vec ** 2)),
        np.min(vec),
        np.max(vec),
        np.percentile(vec, 25),
        np.median(vec),
        np.percentile(vec, 75),
        np.mean((vec - np.mean(vec))**3) / (np.std(vec)**3 + 1e-8),
        np.mean((vec - np.mean(vec))**4) / (np.std(vec)**4 + 1e-8),
        np.sum(vec**2),
        -np.sum((vec_safe/np.sum(vec_safe)) * np.log(vec_safe/np.sum(vec_safe)))
    ])

#preprocessed data
# def load_single_txt_with_features(txt_path):
#     vec = np.loadtxt(txt_path)
#     if vec.ndim != 1:
#         raise ValueError("⚠️ 資料格式錯誤，應為一維向量")

#     fs = 500
#     n_fft = 10000
#     freqs = np.fft.rfftfreq(n_fft, d=1/fs)

#     stat_feat = extract_features(vec)
#     band_feat = extract_band_power(vec, freqs)
#     fused = np.concatenate([vec, stat_feat, band_feat])
#     return fused

def load_single_txt_with_features(txt_path):
    vec = np.loadtxt(txt_path)
    vec = vec[10000:20000]
    fft_result = np.fft.rfft(vec, n=10000)
    power = np.abs(fft_result) ** 2
    log_power = np.log1p(power)
    freqs = np.fft.rfftfreq(10000, d=1/500)

    stat_feat = extract_features(log_power)
    band_feat = extract_band_power(log_power, freqs)

    return np.concatenate([log_power, stat_feat, band_feat])

# === Model ===
class EEGMLP(nn.Module):
    def __init__(self, input_dim, num_classes):
        super(EEGMLP, self).__init__()
        self.model = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.4),
            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.4),
            nn.Linear(64, num_classes)
        )

    def forward(self, x):
        return self.model(x)
    
# === 載入模型與 scaler ===
model = EEGMLP(5019, 4)
model.load_state_dict(torch.load("../model/subject9_best_model_1.pt", map_location=torch.device('cpu')))
model.eval()
scaler = joblib.load("../model/scaler_subject9.pkl")
label_map = ["relax", "concentrating", "stress", "memory"]

def predict_prob(txt_path):
    x_raw = load_single_txt_with_features(txt_path)
    x_scaled = scaler.transform(x_raw.reshape(1, -1))
    x_tensor = torch.tensor(x_scaled, dtype=torch.float32)

    with torch.no_grad():
        output = model(x_tensor)
        prob = torch.softmax(output, dim=1).numpy()[0]
        return {label_map[i]: float(prob[i]) for i in range(4)}

# === Run EEG 推論 ===
# eeg_file = "../raw_data/S09/6.txt"
# eeg_state = predict_prob(eeg_file)
# print("🧠 EEG 分類機率：", eeg_state)