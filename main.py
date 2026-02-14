import akshare as ak
import pandas as pd
import datetime
import time
import sys

def get_stock_list_with_retry(retries=5):
    """
    多策略、多重试抓取全A股列表
    """
    for i in range(retries):
        try:
            print(f"尝试抓取股票列表 (第 {i+1} 次)...")
            # 策略A: 实时行情接口 (最推荐)
            df = ak.stock_zh_a_spot_em()
            if df is not None and not df.empty:
                return dict(zip(df['代码'], df['名称']))
        except Exception as e:
            print(f"策略A失败: {e}")
        
        try:
            # 策略B: 备用接口 - A股代码和名称
            df = ak.stock_info_a_code_name()
            if df is not None and not df.empty:
                return dict(zip(df['code'], df['name']))
        except Exception as e:
            print(f"策略B失败: {e}")
        
        # 如果都失败，等待几秒再重试
        time.sleep(5)
    
    return None

def get_signals(df):
    """
    纯 pandas 计算指标逻辑
    """
    try:
        if len(df) < 65: return False, False
        close = df['收盘'].astype(float)
        high = df['最高'].astype(float)
        low = df['最低'].astype(float)

        def ema(series, n): return series.ewm(span=n, adjust=False).mean()
        def sma_tdx(series, n): return series.ewm(alpha=1/n, adjust=False).mean()

        # 主图金钻
        ma_h = ema(ema(high, 25), 25)
        ma_l = ema(ema(low, 25), 25)
        trend_line = ma_l - (ma_h - ma_l)
        main_yellow = low <= trend_line

        # 副图粉色
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
        print("❌ 错误: 无法获取股票列表，请检查网络或稍后重试。")
        return

    all_codes = list(stock_dict.keys())
    print(f"获取列表成功，共 {len(all_codes)} 只。开始逐一扫描...")

    res_resonance = []
    count = 0
    total = len(all_codes)

    # 为了防止全量扫描太久导致被封，我们可以只扫前1000只做测试，
    # 或者全量扫描但增加容错。这里保持全量。
    for code in all_codes:
        count += 1
        if count % 300 == 0:
            print(f"进度: {count}/{total}...")

        try:
            # 增加少许延迟，防止请求过快被封
            # time.sleep(0.05)
            
            # 抓取历史行情
            df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
            if df is None or df.empty: continue
            
            yellow, pink = get_signals(df)
            if yellow and pink:
                msg = f"🔥 [共振] {code} - {stock_dict[code]}"
                print(msg)
                res_resonance.append(msg)
        except Exception:
            continue

    # 打印最终报表
    print("\n" + "="*40)
    print(f"📅 扫描日期: {datetime.date.today()}")
    print("\n### 💎 强力推荐 (双重共振)")
    if res_resonance:
        for r in res_resonance: print(f"- {r}")
    else:
        print("- 今日暂无符合条件的股票。")
    print("="*40)

if __name__ == "__main__":
    main()
