# -*- coding: utf-8 -*-
"""数据获取模块：优先Wind，兼容公开数据源"""
import pandas as pd
import numpy as np
from tqdm import tqdm
import windpy
from config import *


# 初始化Wind API
def init_wind():
    """初始化Wind连接"""
    windpy.w.start()
    if not windpy.w.isconnected():
        raise ConnectionError("Wind终端未登录或API连接失败！")
    return windpy.w


def get_wind_data(w, code, start_date, end_date, field="close"):
    """
    从Wind获取数据
    :param w: Wind API实例
    :param code: 证券代码
    :param start_date: 起始日期
    :param end_date: 结束日期
    :param field: 字段（close=收盘价/收益率）
    :return: DataFrame（date, value）
    """
    try:
        # Wind API调用
        data = w.wsd(
            code=code,
            fields=field,
            startdate=start_date,
            enddate=end_date,
            options="PriceAdj=B"
        )
        # 转换为DataFrame
        df = pd.DataFrame({
            "date": data.Times,
            "value": data.Data[0]
        })
        # 日期格式化+去重
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        df = df.drop_duplicates(subset=["date"]).reset_index(drop=True)
        # 处理缺失值
        df["value"] = df["value"].interpolate(method="linear")
        df = df.dropna()
        return df
    except Exception as e:
        raise Exception(f"Wind数据获取失败：{str(e)}")


def get_bond_yield(start_date=START_DATE, end_date=END_DATE):
    """
    获取10Y和1Y国债收益率数据
    :return: 合并后的DataFrame（date, yield_10y, yield_1y, spread）
    """
    # 初始化Wind
    w = init_wind()

    # 获取10Y国债收益率
    print("正在获取10年期国债收益率数据...")
    df_10y = get_wind_data(w, CODE_10Y, start_date, end_date)
    df_10y.rename(columns={"value": "yield_10y"}, inplace=True)

    # 获取1Y国债收益率
    print("正在获取1年期国债收益率数据...")
    df_1y = get_wind_data(w, CODE_1Y, start_date, end_date)
    df_1y.rename(columns={"value": "yield_1y"}, inplace=True)

    # 合并数据并计算利差
    df = pd.merge(df_10y, df_1y, on="date", how="inner")
    df["spread"] = df["yield_10y"] - df["yield_1y"]
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # 验证数据
    if len(df) < ROLLING_WINDOW:
        raise ValueError(f"数据量不足（仅{len(df)}条），无法计算{ROLLING_WINDOW}天滚动统计！")

    print(f"数据获取完成：共{len(df)}个交易日，利差均值{df['spread'].mean():.4f}，标准差{df['spread'].std():.4f}")
    return df


# 无Wind权限的替代方案（公开数据源）
def get_public_bond_yield(start_date=START_DATE, end_date=END_DATE):
    """
    从英为财情获取公开国债收益率数据（备用）
    注：需手动确认指标对应关系，确保数据准确性
    """
    import requests
    import json

    # 示例：英为财情10Y/1Y国债收益率接口（需自行验证）
    url_10y = "https://cn.investing.com/rates-bonds/china-10-year-government-bond-yield-historical-data"
    url_1y = "https://cn.investing.com/rates-bonds/china-1-year-government-bond-yield-historical-data"

    # 此处仅为示例框架，需根据实际接口调整
    # 实际使用时需爬取/调用公开API，或手动下载CSV后读取
    df_10y = pd.read_csv("./data/10y_bond_yield.csv")
    df_1y = pd.read_csv("./data/1y_bond_yield.csv")

    df_10y["date"] = pd.to_datetime(df_10y["date"])
    df_1y["date"] = pd.to_datetime(df_1y["date"])

    df = pd.merge(df_10y, df_1y, on="date", how="inner")
    df["spread"] = df["yield_10y"] - df["yield_1y"]
    return df


if __name__ == "__main__":
    # 测试数据获取
    df = get_bond_yield()
    print(df.head())