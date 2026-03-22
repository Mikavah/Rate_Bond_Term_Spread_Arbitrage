# -*- coding: utf-8 -*-
"""回测引擎：计算收益、风控指标、可视化"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from config import *

# 设置中文字体（解决图表中文显示问题）
plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False


class BacktestEngine:
    def __init__(self, df_signal, trade_log_df, initial_capital=INITIAL_CAPITAL):
        """
        初始化回测引擎
        :param df_signal: 带信号的策略数据
        :param trade_log_df: 交易日志
        :param initial_capital: 初始资金
        """
        self.df = df_signal.copy()
        self.trade_log = trade_log_df.copy()
        self.initial_capital = initial_capital
        self.equity_curve = []  # 净值曲线
        self.current_capital = initial_capital

    def calculate_equity(self):
        """计算账户净值曲线"""
        # 初始化净值
        self.df["capital"] = self.initial_capital
        self.df["daily_return"] = 0.0

        # 逐行计算资金变化
        for i in range(len(self.df)):
            if i == 0:
                self.equity_curve.append(self.initial_capital)
                continue

            # 检查是否有平仓交易
            if not self.trade_log.empty:
                trade_on_day = self.trade_log[self.trade_log["date"] == self.df.loc[i, "date"]]
                for _, trade in trade_on_day.iterrows():
                    if trade["type"] == "close":
                        # 平仓盈利计入资金
                        self.current_capital += trade["profit"]

            # 记录当日资金
            self.df.loc[i, "capital"] = self.current_capital
            self.df.loc[i, "daily_return"] = (self.current_capital - self.equity_curve[-1]) / self.equity_curve[-1]
            self.equity_curve.append(self.current_capital)

        self.df["equity"] = self.equity_curve[:-1] if len(self.equity_curve) > len(self.df) else self.equity_curve
        return self.df

    def calculate_metrics(self):
        """计算核心回测指标"""
        # 基础收益指标
        total_return = (self.current_capital - self.initial_capital) / self.initial_capital
        trading_days = len(self.df)
        annual_return = (1 + total_return) ** (250 / trading_days) - 1

        # 风险指标
        daily_returns = self.df["daily_return"].dropna()
        annual_volatility = daily_returns.std() * np.sqrt(250)
        sharpe_ratio = (annual_return - RISK_FREE_RATE) / annual_volatility if annual_volatility != 0 else 0

        # 最大回撤
        equity = self.df["equity"].values
        peak = np.maximum.accumulate(equity)
        drawdown = (equity - peak) / peak
        max_drawdown = np.min(drawdown)

        # 交易指标
        if not self.trade_log.empty:
            close_trades = self.trade_log[self.trade_log["type"] == "close"]
            win_trades = close_trades[close_trades["profit"] > 0]
            win_rate = len(win_trades) / len(close_trades) if len(close_trades) > 0 else 0
            avg_win = win_trades["profit"].mean() if len(win_trades) > 0 else 0
            avg_loss = close_trades[close_trades["profit"] < 0]["profit"].mean() if len(
                close_trades[close_trades["profit"] < 0]) > 0 else 0
            profit_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        else:
            win_rate = 0
            profit_loss_ratio = 0

        # 整理指标
        metrics = {
            "初始资金": self.initial_capital,
            "最终资金": self.current_capital,
            "累计收益率": total_return,
            "年化收益率": annual_return,
            "年化波动率": annual_volatility,
            "夏普比率": sharpe_ratio,
            "最大回撤": max_drawdown,
            "交易次数": len(self.trade_log) // 2 if not self.trade_log.empty else 0,  # 开仓+平仓算一次
            "胜率": win_rate,
            "盈亏比": profit_loss_ratio
        }

        # 转换为DataFrame
        self.metrics_df = pd.DataFrame(metrics.items(), columns=["指标", "数值"])
        return self.metrics_df

    def plot_results(self):
        """绘制可视化图表"""
        # 图1：利差走势+布林带+交易信号
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(PLOT_WIDTH, PLOT_HEIGHT), sharex=True)

        # 利差与布林带
        ax1.plot(self.df["date"], self.df["spread"], label="10Y-1Y利差", color="blue", linewidth=1)
        ax1.plot(self.df["date"], self.df["ma"], label="滚动均值", color="red", linewidth=1.5)
        ax1.plot(self.df["date"], self.df["upper_band"], label="上轨", color="green", linestyle="--")
        ax1.plot(self.df["date"], self.df["lower_band"], label="下轨", color="green", linestyle="--")
        ax1.fill_between(self.df["date"], self.df["lower_band"], self.df["upper_band"], alpha=0.1, color="green")
        ax1.set_ylabel("利差（%）")
        ax1.set_title("10Y-1Y国债利差走势 + 布林带 + 交易信号")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 交易信号
        signals_long = self.df[self.df["signal"] == 1]
        signals_short = self.df[self.df["signal"] == -1]
        ax1.scatter(signals_long["date"], signals_long["spread"], marker="^", color="red", s=50, label="做多利差")
        ax1.scatter(signals_short["date"], signals_short["spread"], marker="v", color="green", s=50, label="做空利差")

        # 图2：账户净值曲线
        ax2.plot(self.df["date"], self.df["equity"], label="账户净值", color="purple", linewidth=1.5)
        ax2.set_xlabel("日期")
        ax2.set_ylabel("账户净值（元）")
        ax2.set_title("账户净值曲线")
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # 保存图表
        plt.tight_layout()
        plt.savefig(f"{RESULTS_DIR}/spread_signal_plot.png", dpi=300, bbox_inches="tight")

        # 图3：每日收益分布
        fig2, ax3 = plt.subplots(1, 1, figsize=(PLOT_WIDTH, PLOT_HEIGHT // 2))
        ax3.hist(self.df["daily_return"].dropna(), bins=50, alpha=0.7, color="blue", edgecolor="black")
        ax3.set_xlabel("每日收益率")
        ax3.set_ylabel("频次")
        ax3.set_title("每日收益率分布")
        ax3.grid(True, alpha=0.3)
        plt.savefig(f"{RESULTS_DIR}/daily_return_hist.png", dpi=300, bbox_inches="tight")

        # 图4：最大回撤曲线
        fig3, ax4 = plt.subplots(1, 1, figsize=(PLOT_WIDTH, PLOT_HEIGHT // 2))
        equity = self.df["equity"].values
        peak = np.maximum.accumulate(equity)
        drawdown = (equity - peak) / peak
        ax4.plot(self.df["date"], drawdown, color="red", linewidth=1)
        ax4.fill_between(self.df["date"], drawdown, 0, alpha=0.3, color="red")
        ax4.set_xlabel("日期")
        ax4.set_ylabel("回撤比例")
        ax4.set_title("最大回撤曲线")
        ax4.grid(True, alpha=0.3)
        plt.savefig(f"{RESULTS_DIR}/drawdown_curve.png", dpi=300, bbox_inches="tight")

        plt.close("all")
        print("可视化图表已保存至results目录！")

    def save_results(self):
        """保存回测结果"""
        # 保存回测指标
        self.metrics_df.to_csv(f"{RESULTS_DIR}/backtest_metrics.csv", index=False, encoding="utf-8-sig")
        # 保存交易日志
        if not self.trade_log.empty:
            self.trade_log.to_csv(f"{RESULTS_DIR}/trade_log.csv", index=False, encoding="utf-8-sig")
        # 保存策略数据
        self.df.to_csv(f"{RESULTS_DIR}/strategy_data.csv", index=False, encoding="utf-8-sig")
        print("回测结果已保存至results目录！")


if __name__ == "__main__":
    # 测试回测
    from data_provider import get_bond_yield
    from strategy import TermSpreadArbitrageStrategy

    # 获取数据
    df_bond = get_bond_yield()
    # 初始化策略
    strategy = TermSpreadArbitrageStrategy(df_bond)
    df = strategy.calculate_bollinger_band()
    df_signal, trade_log = strategy.generate_signal()
    # 初始化回测引擎
    backtest = BacktestEngine(df_signal, trade_log)
    # 计算净值
    df_equity = backtest.calculate_equity()
    # 计算指标
    metrics = backtest.calculate_metrics()
    print("回测指标：")
    print(metrics)
    # 绘制图表
    backtest.plot_results()
    # 保存结果
    backtest.save_results()