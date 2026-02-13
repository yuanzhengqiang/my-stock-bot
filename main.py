import akshare as ak
import pandas as pd
import pandas_ta as ta
import datetime
import time
import sys

def get_signals(df):
    """
    计算主图金钻逻辑和副图粉色信号逻辑
    """
    try:
        # 数据量不足以计算长周期指标则跳过
        if len(df) < 65:
            return False, False
        
        # 提取基础数据
        close = df['收盘'].astype(float)
        high = df['最高'].astype(float)
        low = df['最低'].astype(float)

        # --- 1. 主图逻辑: 金钻趋势 (基于双重平滑近似) ---
        # 通达信 XMA 在 Python 中用双重 EMA 模拟，消除未来函数漂移
        ma_h = ta.ema(ta.ema(high, length=25), length=25)
        ma_l = ta.ema(ta.ema(low, length=25), length=25)
        
        # 金钻趋势线: XMA(L,25)-(XMA(H,25)-XMA(L,25))
        trend_line = ma_l - (ma_h - ma_l)
        
        # 信号：今日最低价触碰或低于趋势线 (即图中的黄线位置)
        main_yellow = low <= trend_line

        # --- 2. 副图逻辑: 股价趋势 & 散户线 (粉色信号) ---
        # A. 散户线 (基于60日高低位)
        hhv_60 = high.rolling(60).max()
        llv_60 = low.rolling(60).min()
        retail_line = 100 * (hhv_60 - close) / (hhv_60 - llv_60)
        # 信号1: 关注低买 (散户线从90以上下穿)
        pink_signal_1 = (retail_line.shift(1) >= 90) & (retail_line < 90)

        # B. 股价趋势 (基于27日平滑)
        # 模拟通达信 SMA(X, N, 1) 即 Alpha=1/N 的 ewm
        stoch_27 = 100 * (close - low.rolling(27).min()) / (high.rolling(27).max() - low.rolling(27).min())
        sma_5 = stoch_27.ewm(alpha=1/5, adjust=False).mean()
        sma_3 = sma_5.ewm(alpha=1/3, adjust=False).mean()
        price_trend = 3 * sma_5 - 2 * sma_3
        # 信号2: 买入警戒 (趋势线进入10以下超卖区)
        pink_signal_2 = price_trend <= 10

        # --- 3. 结果判断 ---
        # 返回今日(最后一行)的布尔值
        is_yellow = main_yellow.iloc[-1]
        is_pink = pink_signal_1.iloc[-1] or pink_signal_2.iloc[-1]
        
        return is_yellow, is_pink

    except Exception as e:
        return False, False

def main():
    print(f"[{datetime.datetime.now()}] 🚀 启动全A股深度扫描任务...")
    
    # 1. 获取全A股实时列表
    try:
        stock_list_df = ak.stock_zh_a_spot_em()
        all_codes = stock_list_df['代码'].tolist()
        stock_dict = dict(zip(stock_list_df['代码'], stock_list_df['名称']))
        print(f"成功抓取全A股列表，共计 {len(all_codes)} 只股票。")
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        return

    res_resonance = []  # 存双重共振信号
    res_yellow = []     # 仅存主图触底信号

    count = 0
    total = len(all_codes)

    # 2. 遍历扫描
    for code in all_codes:
        count += 1
        if count % 100 == 0:
            print(f"进度: {count}/{total}...")

        try:
            # 下载历史行情 (获取最近80天数据足够计算)
            # 使用 try_except 保证单只股票失败不影响全局
            df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
            
            if df is None or df.empty:
                continue
            
            yellow, pink = get_signals(df)
            
            if yellow and pink:
                msg = f"🔥 [双重共振] {code} - {stock_dict[code]}"
                print(msg)
                res_resonance.append(msg)
            elif yellow:
                res_yellow.append(f"🟡 [主图触底] {code} - {stock_dict[code]}")
                
            # 这里的 time.sleep 可以视情况开启，防止被数据源封禁
            # time.sleep(0.05) 

        except Exception:
            continue

    # 3. 打印最终报表 (这个输出将被 GitHub Action 捕获并创建为 Issue)
    print("\n" + "="*40)
    print(f"📅 扫描日期: {datetime.date.today()}")
    print(f"✅ 扫描总量: {total} 只股票")
    print("="*40)
    
    print("\n### 💎 强力推荐 (主副图双重共振)")
    if res_resonance:
        for r in res_resonance:
            print(f"- {r}")
    else:
        print("- 今日暂无符合共振条件的股票。")

    print("\n### 🟡 关注名单 (仅主图触及趋势线)")
    if res_yellow:
        # 如果太多，仅展示前 50 只
        for r in res_yellow[:50]:
            print(f"- {r}")
        if len(res_yellow) > 50:
            print(f"- ... 等共计 {len(res_yellow)} 只。")
    else:
        print("- 无。")

    print("\n" + "="*40)
    print("💡 提示：本结果基于技术指标筛选，仅供参考，不构成投资建议。")

if __name__ == "__main__":
    main()
