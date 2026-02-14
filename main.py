import akshare as ak
import pandas as pd
import datetime
import time
import random

def get_stock_list_with_retry(retries=10):
    """
    针对海外IP极其不稳定的情况，增加多次重试
    """
    for i in range(retries):
        try:
            print(f"尝试抓取全A股列表 (第 {i+1} 次)...")
            # 尝试最常用的接口
            df = ak.stock_zh_a_spot_em()
            if df is not None and not df.empty:
                return dict(zip(df['代码'], df['名称']))
        except Exception as e:
            print(f"尝试失败: {e}")
            # 随机等待 5-15 秒再重试，模仿人类行为
            time.sleep(random.randint(5, 15))
    return None

def get_signals(df):
    try:
        if len(df) < 65: return False, False
        close = df['收盘'].astype(float)
        high = df['最高'].astype(float)
        low = df['最低'].astype(float)

        def ema(series, n): return series.ewm(span=n, adjust=False).mean()
        def sma_tdx(series, n): return series.ewm(alpha=1/n, adjust=False).mean()

        ma_h = ema(ema(high, 25), 25)
        ma_l = ema(ema(low, 25), 25)
        trend_line = ma_l - (ma_h - ma_l)
        main_yellow = low <= trend_line

        hhv_60 = high.rolling(60).max()
        llv_60 = low.rolling(60).min()
        retail_line = 100 * (hhv_60 - close) / (hhv_60 - llv_60)
        pink_1 = (retail_line.shift(1) >= 90) & (retail_line < 90)

        stoch_27 = 100 * (close - low.rolling(27).min()) / (high.rolling(27).max() - low.rolling(27).min())
        sma_5 = sma_tdx(stoch_27, 5)
        sma_3 = sma_tdx(sma_5, 3)
        price_trend = 3 * sma_5 - 2 * sma_3
        pink_2 = price_trend <= 10

        return main_yellow.iloc[-1], (pink_1.iloc[-1] or pink_2.iloc[-1])
    except:
        return False, False

def main():
    print(f"[{datetime.datetime.now()}] 🚀 启动全A股扫描...")
    
    stock_dict = get_stock_list_with_retry()
    if not stock_dict:
        print("❌ 错误: 无法获取股票列表。建议：手动运行 Actions 或更换运行时间。")
        return

    all_codes = list(stock_dict.keys())
    print(f"获取列表成功，共 {len(all_codes)} 只。开始扫描...")

    res_resonance = []
    # 为了防止全量扫描被封IP，我们这里设置只扫前 2000 只最活跃的，或者你也可以保持全量
    # all_codes = all_codes[:2000] 

    for idx, code in enumerate(all_codes):
        if idx % 100 == 0:
            print(f"进度: {idx}/{len(all_codes)}...")

        try:
            # 核心：每次请求稍微歇一下，降低频率
            time.sleep(0.1) 
            
            df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
            if df is None or df.empty: continue
            
            yellow, pink = get_signals(df)
            if yellow and pink:
                msg = f"🔥 [共振] {code} - {stock_dict[code]}"
                print(msg)
                res_resonance.append(msg)
        except:
            # 如果单只股票下载失败（被断开），歇久一点
            time.sleep(1)
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
