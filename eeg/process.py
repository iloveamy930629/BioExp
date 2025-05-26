import numpy as np
import torch
import torch.nn as nn
import torch
import joblib
from scipy.signal import butter, filtfilt

# === 特徵提取 ===
def extract_band_power(vec, freqs):
    bands = {
        "delta": (0.5, 4),
        "theta": (4, 8),
        "alpha": (8, 13),
        "beta": (13, 30),
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

def compute_band_ratios(band_feat):
    theta, alpha, beta = band_feat[1], band_feat[2], band_feat[3]
    return np.array([
        theta / (alpha + 1e-8),
        alpha / (beta + 1e-8),
        beta / (theta + 1e-8)
    ])

# def load_single_txt_with_features(txt_path):
#     fs = 500
#     with open(txt_path, encoding='utf-8') as f:
#         vec = np.loadtxt(f, skiprows=1)

#     # vec = np.loadtxt(txt_path)
#     vec = vec[:10000]
#     fft_result = np.fft.rfft(vec, n=10000)
#     power = np.abs(fft_result) ** 2
#     log_power = np.log1p(power)
#     freqs = np.fft.rfftfreq(10000, d=1/500)

#     stat_feat = extract_features(log_power)
#     band_feat = extract_band_power(log_power, freqs)

#     return np.concatenate([log_power, stat_feat, band_feat])

fs = 500
b_bp, a_bp = butter(N=4, Wn=[0.5, 50], btype='bandpass', fs=fs)

def load_single_txt_with_features(txt_path):
    fs = 500
    raw = np.loadtxt(txt_path, skiprows=1)  # 若檔案無標頭可去掉 skiprows

    # --- 取出 10 秒段落（與訓練一致：起點 12500） ---
    start = (len(raw)-5000)//2
    segment = raw[start : start + 5000]     # 5000 點

    # --- 時域 band-pass 濾波 ---
    filtered = filtfilt(b_bp, a_bp, segment)

    # --- FFT，長度 = 5000（與段長一致） ---
    fft_vals  = np.fft.fft(filtered, n=5000)
    power     = np.abs(fft_vals[:2501])**2      # 前半部 + Nyquist
    log_power = np.log1p(power)

    # --- 頻率對應 ---
    freqs = np.fft.rfftfreq(5000, d=1/fs)
    idx   = (freqs >= 0.5) & (freqs <= 50)
    log_power = log_power[idx]

    # 保留前 496 維
    if len(log_power) < 496:
        raise ValueError(f"log_power 只有 {len(log_power)} (<496)")
    log_power = log_power[:496]
    freqs     = freqs[idx][:496]

    # --- 20 維輔助特徵 ---
    stat_feat  = extract_features(log_power)
    band_feat  = extract_band_power(log_power, freqs)
    ratio_feat = compute_band_ratios(band_feat)

    return np.concatenate([log_power, stat_feat, band_feat, ratio_feat])

# === Model ===
# class EEGMLP(nn.Module):
#     def __init__(self, input_dim, num_classes):
#         super(EEGMLP, self).__init__()
#         self.model = nn.Sequential(
#             nn.Linear(input_dim, 128),
#             nn.BatchNorm1d(128),
#             nn.ReLU(),
#             nn.Dropout(0.4),
#             nn.Linear(128, 64),
#             nn.BatchNorm1d(64),
#             nn.ReLU(),
#             nn.Dropout(0.4),
#             nn.Linear(64, num_classes)
#         )

#     def forward(self, x):
#         return self.model(x)
class HybridCNN(torch.nn.Module):
    def __init__(self, vec_dim, meta_dim, num_classes):
        super().__init__()
        self.cnn = torch.nn.Sequential(
            torch.nn.Conv1d(1, 32, kernel_size=5, padding=2),
            torch.nn.BatchNorm1d(32),
            torch.nn.ReLU(),
            torch.nn.MaxPool1d(2),
            torch.nn.Conv1d(32, 64, kernel_size=5, padding=2),
            torch.nn.BatchNorm1d(64),
            torch.nn.ReLU(),
            torch.nn.AdaptiveAvgPool1d(1),
            torch.nn.Flatten()
        )
        self.mlp = torch.nn.Sequential(
            torch.nn.Linear(meta_dim, 64),
            torch.nn.ReLU(),
            torch.nn.Dropout(0.3)
        )
        self.classifier = torch.nn.Sequential(
            torch.nn.Linear(64 + 64, 64),
            torch.nn.ReLU(),
            torch.nn.Dropout(0.3),
            torch.nn.Linear(64, num_classes)
        )

    def forward(self, x):
        vec = x[:, :496].unsqueeze(1)
        meta = x[:, 496:]
        cnn_out = self.cnn(vec)
        mlp_out = self.mlp(meta)
        return self.classifier(torch.cat([cnn_out, mlp_out], dim=1))

# === 載入模型與 scaler ===
# model = EEGMLP(5019, 4)
# model.load_state_dict(torch.load("../model/best_hybrid_model.pt", map_location=torch.device('cpu')))
# model.eval()
# scaler = joblib.load("../model/best_scaler.pkl")
label_map = ["relax", "concentrating", "stress", "memory"]

VEC_DIM = 496           # log-power 部分
META_DIM = 20           # 統計+band+ratio
NUM_CLASSES = 4
model = HybridCNN(vec_dim=VEC_DIM, meta_dim=META_DIM, num_classes=NUM_CLASSES)
model.load_state_dict(torch.load("../model/best_model_subject18.pt", map_location=torch.device('cpu')))
model.eval()
scaler = joblib.load("../model/scaler_subject18.pkl")

def predict_prob(txt_path):
    x_raw = load_single_txt_with_features(txt_path)
    x_scaled = scaler.transform(x_raw.reshape(1, -1))

    nan_mask = np.isnan(x_scaled[0])
    if nan_mask.any():
        print("NaN 出現在這些維度：", np.where(nan_mask)[0])
        print("對應原始特徵值：", x_raw[np.where(nan_mask)[0]])
        print("scaler.mean_：", scaler.mean_[np.where(nan_mask)[0]])
        print("scaler.scale_：", scaler.scale_[np.where(nan_mask)[0]])
        raise ValueError("❌ x_scaled 出現 NaN")

    if np.isnan(x_scaled).any():
        raise ValueError("❌ x_scaled 出現 NaN")
    if np.isinf(x_scaled).any():
        raise ValueError("❌ x_scaled 出現 inf")

    x_tensor = torch.tensor(x_scaled, dtype=torch.float32)
    with torch.no_grad():
        output = model(x_tensor)
        if torch.isnan(output).any():
            raise ValueError("❌ 模型輸出出現 NaN")
        prob = torch.softmax(output, dim=1).numpy()[0]
        return {label_map[i]: float(prob[i]) for i in range(4)}


# === Run EEG 推論 ===
# eeg_file = "../data/data_relax.txt"
# eeg_state = predict_prob(eeg_file)
# print("🧠 EEG 分類機率：", eeg_state)