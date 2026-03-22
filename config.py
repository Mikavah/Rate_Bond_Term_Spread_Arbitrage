# 数据参数
START_DATE = "2018-01-01"  # 回测起始日期
END_DATE = "2025-03-01"    # 回测结束日期
ROLLING_WINDOW = 60        # 滚动窗口长度（交易日）
SIGMA_MULTIPLIER = 2       # 标准差倍数（布林带宽度）

# 风控参数
STOP_LOSS_RATIO = 0.005    # 单笔止损比例（0.5%）
MAX_POSITION_RATIO = 0.5   # 最大仓位比例（50%）
MAX_HOLD_DAYS = 20         # 最大持仓天数