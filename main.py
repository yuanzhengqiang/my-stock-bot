import akshare as ak
import pandas as pd
import pandas_ta as ta
import time

def get_signals(df):
    try:
        if len(df) < 60: return False, False
        close = df['收盘']
        high = df['最高']
        low = df['最低']
        
        # --- 主图逻辑 (金钻趋势) ---
        ma_h = ta.ema(ta.ema(high, length=25), length=25)
        ma_l = ta.ema(ta.ema(low, length=25), length=25)
        trend_line = ma_l - (ma_h - ma_l)
        main_yellow = low <= trend_line

        # --- 副图逻辑 (粉色信号) ---
        hhv_60 = high.rolling(60).max()
        llv_60 = low.rolling(60).min()
        retail_line = 100 * (hhv_60 - close) / (hhv_60 - llv_60)
        pink_1 = (retail_line.shift(1) >= 90) & (retail_line < 90)

        stoch_27 = 100 * (close - low.rolling(27).min()) / (high.rolling(27).max() - low.rolling(27).min())
        sma_5 = stoch_27.ewm(alpha=1/5, adjust=False).mean()
        sma_3 = sma_5.ewm(alpha=1/3, adjust=False).mean()
        price_trend = 3 * sma_5 - 2 * sma_3
        pink_2 = price_trend <= 10

        return main_yellow.iloc[-1], (pink_1.iloc[-1] or pink_2.iloc[-1])
    except:
        return False, False

# 1. 获取全A股实时行情列表（为了拿到所有代码）
print("正在获取全A股列表...")
stock_zh_a_spot_em_df = ak.stock_zh_a_spot_em()
all_codes = stock_zh_a_spot_em_df['代码'].tolist()
all_names = stock_zh_a_spot_em_df['名称'].tolist()
stock_dict = dict(zip(all_codes, all_names))

print(f"成功获取 {len(all_codes)} 只股票，开始遍历扫描...")

results = []

# 2. 遍历扫描
for code in all_codes:
    try:
        # 获取历史行情 (获取最近80天数据足够计算指标)
        df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
        if df.empty: continue
        
        yellow, pink = get_signals(df)
        
        if yellow and pink:
            msg = f"🔥 [双重共振] {code} - {stock_dict[code]}"
            print(msg)
            results.append(msg)
        elif yellow:
            # print(f"🟡 [主图触底] {code}") # 如果不想日志太乱，可以取消主图提示
            pass
            
        # 适当减速，防止被封IP (每秒抓取2-3只)
        # time.sleep(0.1) 
        
    except Exception as e:
        continue

# 3. 输出最终报告
print("\n" + "="*30)
print(f"扫描完毕！今日符合指标股票如下：")
if results:
    print("\n".join(results))
else:
    print("今日全市场无共振买点。")
print("="*30)
