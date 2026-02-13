import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np

def get_combined_signals(df):
    """
    整合主图(金钻趋势)与副图(股价趋势)的逻辑
    """
    # 基础数据
    close = df['Close']
    high = df['High']
    low = df['Low']
    
    # --- 主图逻辑 (金钻趋势) ---
    # 使用双重 EMA 模拟 XMA (因为 XMA 是未来函数，实盘需用 EMA 代替)
    ma_h = ta.ema(ta.ema(high, length=25), length=25)
    ma_l = ta.ema(ta.ema(low, length=25), length=25)
    trend_line = ma_l - (ma_h - ma_l)
    
    # 主图信号：价格触碰或低于趋势线 (你说的黄线位置)
    main_yellow_signal = low <= trend_line

    # --- 副图逻辑 (粉色信号) ---
    # 1. 散户线 (类似反向威廉指标)
    hhv_60 = high.rolling(60).max()
    llv_60 = low.rolling(60).min()
    retail_line = 100 * (hhv_60 - close) / (hhv_60 - llv_60)
    # 关注低买: CROSS(90, 散户线) -> 散户线从90以上穿下来
    pink_signal_1 = (retail_line.shift(1) >= 90) & (retail_line < 90)

    # 2. 股价趋势 (3*SMA - 2*SMA)
    # 通达信 SMA(X, 5, 1) 相当于 Alpha=1/5 的 ewm
    stoch_27 = 100 * (close - low.rolling(27).min()) / (high.rolling(27).max() - low.rolling(27).min())
    sma_5 = stoch_27.ewm(alpha=1/5, adjust=False).mean()
    sma_3 = sma_5.ewm(alpha=1/3, adjust=False).mean()
    price_trend = 3 * sma_5 - 2 * sma_3
    # 买入警戒: 股价趋势 <= 10
    pink_signal_2 = price_trend <= 10

    # --- 综合判断 ---
    # 主图出现黄线 且 副图出现粉色信号之一
    is_bottom = main_yellow_signal & (pink_signal_1 | pink_signal_2)
    
    return {
        "is_bottom": is_bottom.iloc[-1],
        "main_yellow": main_yellow_signal.iloc[-1],
        "sub_pink": (pink_signal_1 | pink_signal_2).iloc[-1],
        "price_trend": price_trend.iloc[-1]
    }

# ---------------------------------------------------------
# GitHub Actions 运行主逻辑
# ---------------------------------------------------------
stocks = ["TSLA", "AAPL", "NVDA", "MSFT", "BABA"] # 在这里添加你的股票池

print("🔍 每日深度扫描开始...")
for s in stocks:
    try:
        # 下载数据
        data = yf.download(s, period="100d", interval="1d", progress=False)
        if len(data) < 60: continue
        
        res = get_combined_signals(data)
        
        if res["is_bottom"]:
            print(f"🚀 [强力推荐] {s}: 主副图共振底部！")
        elif res["main_yellow"]:
            print(f"🟡 [主图提示] {s}: 触及金钻支撑线。")
        elif res["sub_pink"]:
            print(f"🌸 [副图提示] {s}: 趋势超卖，关注反弹。")
            
    except Exception as e:
        print(f"❌ {s} 计算出错: {e}")
