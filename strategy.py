# -*- coding: utf-8 -*-
"""策略核心模块：信号生成、头寸管理"""
import pandas as pd
import numpy as np
from config import *


class TermSpreadArbitrageStrategy:
    def __init__(self, df_bond):
        """
        初始化策略
        :param df_bond: 包含yield_10y, yield_1y, spread的DataFrame
        """
        self.df = df_bond.copy()
        self.trade_log = []  # 交易日志
        self.current_position = 0  # 当前仓位：1=做多利差，-1=做空利差，0=空仓
        self.hold_days = 0  # 当前持仓天数
        self.entry_spread = 0  # 开仓时的利差
        self.entry_capital = 0  # 开仓占用资金

    def calculate_bollinger_band(self):
        """计算布林带（滚动均值+标准差）"""
        # 滚动均值
        self.df["ma"] = self.df["spread"].rolling(window=ROLLING_WINDOW).mean()
        # 滚动标准差
        self.df["std"] = self.df["spread"].rolling(window=ROLLING_WINDOW).std()
        # 上轨/下轨
        self.df["upper_band"] = self.df["ma"] + SIGMA_MULTIPLIER * self.df["std"]
        self.df["lower_band"] = self.df["ma"] - SIGMA_MULTIPLIER * self.df["std"]
        # 中性区间上下限
        self.df["neutral_upper"] = self.df["ma"] + 0.5 * self.df["std"]
        self.df["neutral_lower"] = self.df["ma"] - 0.5 * self.df["std"]
        # 剔除滚动窗口内的无效数据
        self.df = self.df.dropna().reset_index(drop=True)
        return self.df

    def generate_signal(self):
        """生成交易信号：1=做多利差，-1=做空利差，0=平仓/空仓"""
        self.df["signal"] = 0
        self.df["position"] = 0  # 实际持仓

        # 逐行判断信号
        for i in range(len(self.df)):
            date = self.df.loc[i, "date"]
            spread = self.df.loc[i, "spread"]
            upper_band = self.df.loc[i, "upper_band"]
            lower_band = self.df.loc[i, "lower_band"]
            neutral_upper = self.df.loc[i, "neutral_upper"]
            neutral_lower = self.df.loc[i, "neutral_lower"]

            # 空仓状态：判断开仓信号
            if self.current_position == 0:
                # 利差低于下轨：做多利差
                if spread < lower_band:
                    self.df.loc[i, "signal"] = 1
                    self.current_position = 1
                    self.hold_days = 0
                    self.entry_spread = spread
                    self.entry_capital = INITIAL_CAPITAL * MAX_POSITION_RATIO
                    # 记录开仓
                    self.trade_log.append({
                        "date": date,
                        "type": "open",
                        "direction": "long_spread",
                        "entry_spread": spread,
                        "capital": self.entry_capital
                    })
                # 利差高于上轨：做空利差
                elif spread > upper_band:
                    self.df.loc[i, "signal"] = -1
                    self.current_position = -1
                    self.hold_days = 0
                    self.entry_spread = spread
                    self.entry_capital = INITIAL_CAPITAL * MAX_POSITION_RATIO
                    # 记录开仓
                    self.trade_log.append({
                        "date": date,
                        "type": "open",
                        "direction": "short_spread",
                        "entry_spread": spread,
                        "capital": self.entry_capital
                    })
            # 持仓状态：判断平仓信号
            else:
                self.hold_days += 1
                # 计算浮亏（用于止损）
                if self.current_position == 1:
                    # 做多利差：利差上涨盈利，下跌亏损
                    float_loss = (self.entry_spread - spread) * self.entry_capital / 10000  # 1bp对应收益调整
                else:
                    # 做空利差：利差下跌盈利，上涨亏损
                    float_loss = (spread - self.entry_spread) * self.entry_capital / 10000

                # 平仓条件：回归中性区间/止损/持仓超期
                close_conditions = [
                    (self.current_position == 1 and spread > neutral_upper),  # 做多利差回归
                    (self.current_position == -1 and spread < neutral_lower),  # 做空利差回归
                    float_loss >= self.entry_capital * STOP_LOSS_RATIO,  # 止损
                    self.hold_days >= MAX_HOLD_DAYS  # 持仓超期
                ]

                if any(close_conditions):
                    self.df.loc[i, "signal"] = 0
                    # 计算平仓收益
                    if self.current_position == 1:
                        profit = (spread - self.entry_spread) * self.entry_capital / 10000
                        direction = "long_spread"
                    else:
                        profit = (self.entry_spread - spread) * self.entry_capital / 10000
                        direction = "short_spread"

                    # 记录平仓
                    self.trade_log.append({
                        "date": date,
                        "type": "close",
                        "direction": direction,
                        "entry_spread": self.entry_spread,
                        "exit_spread": spread,
                        "profit": profit,
                        "capital": self.entry_capital
                    })

                    # 重置持仓状态
                    self.current_position = 0
                    self.hold_days = 0
                    self.entry_spread = 0
                    self.entry_capital = 0

            # 记录实际持仓
            self.df.loc[i, "position"] = self.current_position

        # 转换交易日志为DataFrame
        self.trade_log_df = pd.DataFrame(self.trade_log) if self.trade_log else pd.DataFrame()
        return self.df, self.trade_log_df


if __name__ == "__main__":
    # 测试策略
    from data_provider import get_bond_yield

    df_bond = get_bond_yield()
    strategy = TermSpreadArbitrageStrategy(df_bond)
    df = strategy.calculate_bollinger_band()
    df_signal, trade_log = strategy.generate_signal()
    print("信号生成完成，交易日志：")
    print(trade_log.head())