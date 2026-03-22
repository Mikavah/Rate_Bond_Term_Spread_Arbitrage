# -*- coding: utf-8 -*-
"""主运行文件：整合数据、策略、回测全流程"""
import warnings

warnings.filterwarnings("ignore")  # 忽略无关警告

from data_provider import get_bond_yield
from strategy import TermSpreadArbitrageStrategy
from backtest import BacktestEngine
from config import *


def main():
    """主函数：执行完整策略流程"""
    print("=" * 50)
    print("开始运行利率债期限利差套利策略")
    print(f"回测区间：{START_DATE} 至 {END_DATE}")
    print(f"初始资金：{INITIAL_CAPITAL:,} 元")
    print("=" * 50)

    # 步骤1：获取数据
    try:
        df_bond = get_bond_yield()
    except Exception as e:
        print(f"数据获取失败，尝试备用数据源：{str(e)}")
        from data_provider import get_public_bond_yield
        df_bond = get_public_bond_yield()

    # 步骤2：初始化策略并计算布林带
    strategy = TermSpreadArbitrageStrategy(df_bond)
    df = strategy.calculate_bollinger_band()

    # 步骤3：生成交易信号
    df_signal, trade_log = strategy.generate_signal()
    print(f"\n策略信号生成完成，共生成{len(trade_log)}条交易记录")

    # 步骤4：回测分析
    backtest = BacktestEngine(df_signal, trade_log)
    df_equity = backtest.calculate_equity()
    metrics = backtest.calculate_metrics()

    # 步骤5：输出回测指标
    print("\n" + "=" * 50)
    print("核心回测指标")
    print("=" * 50)
    for _, row in metrics.iterrows():
        if "收益率" in row["指标"] or "回撤" in row["指标"] or "比率" in row["指标"]:
            print(f"{row['指标']}: {row['数值']:.4f}")
        else:
            print(f"{row['指标']}: {row['数值']:,}")

    # 步骤6：绘制并保存结果
    backtest.plot_results()
    backtest.save_results()

    print("\n" + "=" * 50)
    print("策略运行完成！结果已保存至results目录")
    print("=" * 50)


if __name__ == "__main__":
    main()