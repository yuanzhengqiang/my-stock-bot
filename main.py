import akshare as ak
import pandas as pd
import datetime
import time

def get_signals(df):
    """
    使用纯 pandas 计算指标，不再依赖 pandas-ta
    """
    try:
        if len(df) < 65:
            return False, False
        
        # 转换数据类型
        close = df['收盘'].astype(float)
        high = df['最高'].astype(float)
        low = df['最低'].astype(float)

        # --- 1. 主图逻辑: 金钻趋势 (双重 EMA 模拟) ---
        # pandas 自带 ewm 函数计算 EMA
        def ema(series, n):
            return series.ewm(span=n, adjust=False).mean()

        ma_h = ema(ema(high, 25), 25)
        ma_l = ema(ema(low, 25), 25)
        
        # 金钻趋势线
        trend_line = ma_l - (ma_h - ma_l)
        main_yellow = low <= trend_line

        # --- 2. 副图逻辑: 股价趋势 & 散户线 ---
        # A. 散户线 (60日内最高/最低)
        hhv_60 = high.rolling(60).max()
        llv_60 = low.rolling(60).min()
        retail_line = 100 * (hhv_60 - close) / (hhv_60 - llv_60)
        pink_signal_1 = (retail_line.shift(1) >= 90) & (retail_line < 90)

        # B. 股价趋势
        # SMA(X, 27, 1) 在通达信里等于 alpha=1/27 的 ewm
        def sma_tdx(series, n):
            return series.ewm(alpha=1/n, adjust=False).mean()

        stoch_27 = 100 * (close - low.rolling(27).min()) / (high.rolling(27).max() - low.rolling(27).min())
        sma_5 = sma_tdx(stoch_27, 5)
        sma_3 = sma_tdx(sma_5, 3)
        price_trend = 3 * sma_5 - 2 * sma_3
        pink_signal_2 = price_trend <= 10

        # --- 3. 结果判断 ---
        is_yellow = main_yellow.iloc[-1]
        is_pink = pink_signal_1.iloc[-1] or pink_signal_2.iloc[-1]
        
        return is_yellow, is_pink

    except Exception:
        return False, False

def main():
    print(f"[{datetime.datetime.now()}] 🚀 启动全A股扫描(不依赖第三方指标库)...")
    
    try:
        stock_list_df = ak.stock_zh_a_spot_em()
        all_codes = stock_list_df['代码'].tolist()
        stock_dict = dict(zip(stock_list_df['代码'], stock_list_df['名称']))
        print(f"获取列表成功，共 {len(all_codes)} 只。")
    except Exception as e:
        print(f"列表获取失败: {e}")
        return

    res_resonance = []
    count = 0
    total = len(all_codes)

    for code in all_codes:
        count += 1
        if count % 200 == 0: print(f"进度: {count}/{total}...")

        try:
            # 仅抓取最近80天，速度最快
            df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
            if df is None or df.empty: continue
            
            yellow, pink = get_signals(df)
            if yellow and pink:
                msg = f"🔥 [共振] {code} - {stock_dict[code]}"
                print(msg)
                res_resonance.append(msg)
        except:
            continue

    print("\n" + "="*40)
    print(f"📅 扫描日期: {datetime.date.today()}")
    print("\n### 💎 强力推荐 (双重共振)")
    if res_resonance:
        for r in res_resonance: print(f"- {r}")
    else:
        print("- 今日暂无共振买点。")
    print("="*40)

if __name__ == "__main__":
    main()
