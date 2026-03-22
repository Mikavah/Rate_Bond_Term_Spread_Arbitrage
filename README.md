# 固收量化交易策略项目：利率债利差套利策略
## 项目介绍
本项目聚焦利率债核心套利策略——10年期与1年期国债利差期限套利，基于**均值回归理论**构建量化交易模型，涵盖数据获取（Wind/公开数据源）、策略逻辑实现、回测分析全流程，完全贴合固收量化交易岗位的实际工作场景。策略具备参数可调整、风险可控、回测指标完善的特点，可直接用于账户业绩管理、交易策略优化及内部系统开发参考。

## 核心数学模型
### 1. 利差计算模型
核心逻辑：10Y与1Y国债的收益率差是反映期限溢价的核心指标，公式如下：
$$spread_t = Y_{10Y,t} - Y_{1Y,t}$$
其中：
- $Y_{10Y,t}$：t时刻10年期国债收益率（中债国债到期收益率：10年，Wind代码：CBA01011.CS）
- $Y_{1Y,t}$：t时刻1年期国债收益率（中债国债到期收益率：1年，Wind代码：CBA01001.CS）
- 数据维度：日频数据（交易日），对齐时间维度（剔除非交易日），异常值用线性插值填充。

### 2. 滚动统计模型（布林轨）
采用**滚动窗口**计算利差的均值和标准差，捕捉短期统计特征（默认窗口60个交易日）：
$$\mu_t = \frac{1}{N}\sum_{i=t-N+1}^{t} spread_i$$
$$\sigma_t = \sqrt{\frac{1}{N-1}\sum_{i=t-N+1}^{t} (spread_i - \mu_t)^2}$$
其中：
- $N$：滚动窗口长度（默认60个交易日，可动态调整）；
- $\mu_t$：t时刻利差的滚动均值；
- $\sigma_t$：t时刻利差的滚动标准差。

### 3. 交易信号阈值与生成规则
#### （1）交易信号阈值
$$upper\_band_t = \mu_t + k \times \sigma_t \quad (k=2，默认)$$
$$lower\_band_t = \mu_t - k \times \sigma_t \quad (k=2，默认)$$
$$中性区间：[\mu_t - 0.5\sigma_t, \mu_t + 0.5\sigma_t]$$

#### （2）交易信号生成规则
| 信号类型 | 触发条件 | 头寸方向 | 仓位计算 |
|----------|----------|----------|----------|
| 做多利差 | $spread_t < lower\_band_t$ | 做空1Y国债，做多10Y国债 | 总资金 × 最大仓位比例（默认50%） |
| 做空利差 | $spread_t > upper\_band_t$ | 做多1Y国债，做空10Y国债 | 总资金 × 最大仓位比例（默认50%） |
| 止盈平仓 | $spread_t \in [\mu_t - 0.5\sigma_t, \mu_t + 0.5\sigma_t]$ | 平掉所有头寸 | 0 |
| 止损平仓 | 浮亏 ≥ 本金 × 止损比例（默认0.5%） | 平掉所有头寸 | 0 |
| 强制平仓 | 持仓天数 ≥ 最大持仓周期（默认20天） | 平掉所有头寸 | 0 |

### 4. 收益与风险指标计算模型
#### （1）单笔交易收益
$$profit = (spread_{close} - spread_{open}) \times position \times duration\_adjustment$$
其中：
- $duration\_adjustment$：久期调整因子（10Y国债久期≈9，1Y国债久期≈0.9，保证利差1bp变动对应固定收益）；
- $spread_{open}$：开仓时利差；$spread_{close}$：平仓时利差；$position$：持仓仓位。

#### （2）核心回测指标
- 年化收益率：
  $$annual\_return = (1 + total\_return)^{\frac{250}{trading\_days}} - 1$$
- 夏普比率（无风险利率取1Y国债均值，默认2.5%）：
  $$sharpe = \frac{annual\_return - risk\_free\_rate}{\sqrt{annual\_volatility}}$$
- 最大回撤：
  $$max\_drawdown = \min\left(\frac{equity_t - \max_{0 \leq i \leq t}(equity_i)}{\max_{0 \leq i \leq t}(equity_i)}\right)$$

## 项目文件结构
RateBondTermSpreadArbitrage/
├── config.py # 策略参数配置（可灵活调整）
├── data_provider.py # 数据获取模块（Wind / 公开数据源）
├── strategy.py # 策略核心逻辑（信号生成、头寸管理）
├── backtest.py # 回测引擎（收益计算、指标分析、可视化）
├── main.py # 主运行文件（整合全流程）
├── requirements.txt # 依赖包列表
└── results/ # 回测结果输出（指标、图表、交易日志）

## 策略执行流程
### 流程说明
1. **配置层**：灵活调整参数，适配不同市场环境；
2. **数据层**：优先Wind专业数据源，保证数据真实性；
3. **指标层**：基于布林带的均值回归逻辑，贴合机构常用策略框架；
4. **信号层**：多维度平仓规则（止盈/止损/持仓超期），控制风险；
5. **回测层**：覆盖收益/风险/交易三类核心指标，满足业绩考核需求；
6. **优化层**：预留扩展空间，贴合岗位「优化量化模型/开发交易系统」要求。

## 核心代码实现
### 1. 配置文件（config.py）
```python
# -*- coding: utf-8 -*-
"""策略配置文件：所有参数可灵活调整"""
import os

# ===================== 数据参数 =====================
START_DATE = "2018-01-01"  # 回测起始日期
END_DATE = "2025-03-01"    # 回测结束日期
CODE_10Y = "CBA01011.CS"   # 10年期国债收益率（Wind代码）
CODE_1Y = "CBA01001.CS"    # 1年期国债收益率（Wind代码）
ROLLING_WINDOW = 60        # 滚动窗口长度（交易日）
SIGMA_MULTIPLIER = 2       # 标准差倍数（布林带宽度）

# ===================== 风控参数 =====================
STOP_LOSS_RATIO = 0.005    # 单笔止损比例（0.5%）
MAX_POSITION_RATIO = 0.5   # 最大仓位比例（50%）
MAX_HOLD_DAYS = 20         # 最大持仓天数
INITIAL_CAPITAL = 10000000 # 初始资金（1000万，模拟机构账户）
RISK_FREE_RATE = 0.025     # 无风险利率（2.5%）

# ===================== 输出参数 =====================
RESULTS_DIR = "./results"  # 结果保存目录
PLOT_WIDTH = 12            # 图表宽度
PLOT_HEIGHT = 8            # 图表高度

# 创建结果目录
if not os.path.exists(RESULTS_DIR):
    os.makedirs(RESULTS_DIR)

## 环境配置
### 1. 依赖包安装
```bash
pip install -r requirements.txt
