# -*- coding: utf-8 -*-
"""
clean_dataset.py
数据来源：GitHub 公开仓库 xjtulyc/Electric_Vehicle_Crawler 的“充电桩”目录
          （https://github.com/xjtulyc/Electric_Vehicle_Crawler ，数据抓取自公开的充电站信息）
原始文件：data_raw/*.xlsx，共 33 个省级文件
处理流程：读取 → 字段解析 → 去重 → 缺失值处理 → 异常值处理 → 入库 + 导出 CSV
输出：database/analytics.db（表 charging_stations）、data/charging_stations.csv、docs/cleaning_report.json
"""
import glob
import json
import os
import re
import sys

import pandas as pd

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(PROJECT_DIR, "data_raw")
DB_PATH = os.path.join(PROJECT_DIR, "database", "analytics.db")
CSV_PATH = os.path.join(PROJECT_DIR, "data", "charging_stations.csv")
REPORT_PATH = os.path.join(PROJECT_DIR, "docs", "cleaning_report.json")

PROVINCE_MAP = {
    "北京": "北京市", "天津": "天津市", "上海": "上海市", "重庆": "重庆市",
    "河北": "河北省", "山西": "山西省", "辽宁": "辽宁省", "吉林": "吉林省",
    "黑龙江": "黑龙江省", "江苏": "江苏省", "浙江": "浙江省", "安徽": "安徽省",
    "福建": "福建省", "江西": "江西省", "山东": "山东省", "河南": "河南省",
    "湖北": "湖北省", "湖南": "湖南省", "广东": "广东省", "海南": "海南省",
    "四川": "四川省", "贵州": "贵州省", "云南": "云南省", "陕西": "陕西省",
    "甘肃": "甘肃省", "青海": "青海省", "内蒙古": "内蒙古自治区",
    "广西": "广西壮族自治区", "西藏": "西藏自治区", "宁夏": "宁夏回族自治区",
    "新疆": "新疆维吾尔自治区", "香港": "香港特别行政区", "澳门": "澳门特别行政区",
}
MUNICIPALITIES = {"北京市", "天津市", "上海市", "重庆市"}

TIME_PRICE_RE = re.compile(r"\d{1,2}:\d{2}\s*[-~]\s*\d{1,2}:\d{2}\s*[:：]\s*(\d+(?:\.\d+)?)")
LABEL_PRICE_RE = re.compile(r"(?:电价|服务费)[:：]\s*(\d+(?:\.\d+)?)")
RANGE_PRICE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*[-~]\s*(\d+(?:\.\d+)?)\s*元")
CITY_RE = re.compile(r"([\u4e00-\u9fa5]{2,6}?市)")
EMPTY_PRICE_WORDS = ("不详", "未设置", "暂无", "未知")


def parse_city(address, province):
    """从地址里解析城市；直辖市直接返回市名，解析不到记为“未知”。"""
    if province in MUNICIPALITIES:
        return province
    if province in ("香港特别行政区", "澳门特别行政区"):
        return province
    addr = str(address)
    # 去掉省份前缀（全称/简称），避免把省名里的“市”误当城市
    for name in (province, province.replace("省", "").replace("市", ""),
                 province.replace("自治区", "").replace("特别行政区", "")):
        if name and addr.startswith(name):
            addr = addr[len(name):]
            break
    addr = addr.replace("市辖区", "")
    match = CITY_RE.search(addr)
    return match.group(1) if match else "未知"


def parse_avg_price(text):
    """从费用文本里取出价格求平均，兼容原始数据里出现的 5 种写法：
       1) 电费:00:00~06:00:0.45,06:00~08:00:0.814,...
       2) 00:00-06:00:0.8200;06:00-08:00:0.8200;...
       3) 时间段:00:00-06:00,电价:0.500;...
       4) 0.2775-1.0574元/度（区间，取中点）
       5) 1.20（单一价格）；“不详/未设置/暂无”按缺失处理
    """
    if pd.isna(text):
        return None
    s = str(text).replace("充电费：", "").replace("服务费：", "")
    s = re.sub(r"\s+", "", s)
    if not s or any(w in s for w in EMPTY_PRICE_WORDS):
        return None
    prices = [float(x) for x in TIME_PRICE_RE.findall(s)]
    if not prices:
        prices = [float(x) for x in LABEL_PRICE_RE.findall(s)]
    if not prices:
        pairs = RANGE_PRICE_RE.findall(s)
        prices = [(float(a) + float(b)) / 2 for a, b in pairs]
    if not prices:
        match = re.match(r"^(\d+(?:\.\d+)?)", s)
        if match:
            prices = [float(match.group(1))]
    return round(sum(prices) / len(prices), 3) if prices else None


def parse_fast_counts(value):
    if pd.isna(value):
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def main():
    files = sorted(glob.glob(os.path.join(RAW_DIR, "*.xlsx")))
    if not files:
        print("找不到 data_raw/*.xlsx，请先运行 download_dataset.py")
        sys.exit(1)

    frames = []
    for path in files:
        short = os.path.splitext(os.path.basename(path))[0]
        province = PROVINCE_MAP.get(short)
        if province is None:
            print("跳过未知省份文件:", short)
            continue
        df = pd.read_excel(path)
        df["province"] = province
        frames.append(df)
    raw = pd.concat(frames, ignore_index=True)
    report = {"source": "https://github.com/xjtulyc/Electric_Vehicle_Crawler",
              "raw_files": len(files), "raw_rows": int(len(raw))}

    # 1) 字段解析
    raw["fast_piles"] = raw["快充数量"].apply(parse_fast_counts)
    raw["slow_piles"] = raw["慢充数量"].apply(parse_fast_counts)
    raw["electricity_price"] = raw["充电费"].apply(parse_avg_price)
    raw["service_price"] = raw["服务费"].apply(parse_avg_price)
    raw["city"] = [parse_city(a, p) for a, p in zip(raw["地址"], raw["province"])]
    raw["parking_free"] = raw["停车费"].astype(str).str.contains("免费").astype(int)
    raw["open_24h"] = raw["开放时间"].astype(str).str.contains("00:00-24:00").astype(int)
    report["price_parse_missing"] = int(raw["electricity_price"].isna().sum())
    report["service_parse_missing"] = int(raw["service_price"].isna().sum())
    report["city_unknown"] = int((raw["city"] == "未知").sum())

    # 2) 去重
    before = len(raw)
    raw = raw.drop_duplicates(subset=["名称", "地址"])
    report["removed_duplicates"] = int(before - len(raw))

    # 3) 无效/异常记录：快慢充都为空或都超过 500 个（明显是录入异常）
    before = len(raw)
    valid = raw[(raw["fast_piles"] + raw["slow_piles"] > 0)
                & (raw["fast_piles"] <= 500) & (raw["slow_piles"] <= 500)]
    report["removed_invalid"] = int(before - len(valid))
    raw = valid

    # 4) 异常价格（<=0 或 >3 元/度，正常充电价格不会落在这个区间外）先置空再填充
    before_total = len(raw)
    outlier_rows = 0
    for col in ("electricity_price", "service_price"):
        mask = (raw[col] <= 0) | (raw[col] > 3)
        outlier_rows = max(outlier_rows, int(mask.sum()))
        raw.loc[mask, col] = None
    report["price_outliers"] = outlier_rows

    # 5) 价格缺失用同省中位数填充，并记录填充条数
    filled_e = filled_s = 0
    for col in ("electricity_price", "service_price"):
        median = raw.groupby("province")[col].transform("median")
        mask = raw[col].isna()
        raw.loc[mask, col] = median[mask]
        raw[col] = raw[col].fillna(raw[col].median())
        if col == "electricity_price":
            filled_e = int(mask.sum())
        else:
            filled_s = int(mask.sum())
    report["filled_electricity_price"] = filled_e
    report["filled_service_price"] = filled_s

    raw["total_piles"] = raw["fast_piles"] + raw["slow_piles"]
    raw["total_price"] = (raw["electricity_price"] + raw["service_price"]).round(3)
    raw["scale_level"] = pd.cut(raw["total_piles"], bins=[0, 5, 10, 20, 10 ** 6],
                                labels=["小型站(1-5桩)", "中型站(6-10桩)",
                                        "大型站(11-20桩)", "超大型站(20桩以上)"]).astype(str)

    # 5) 入库
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    out = pd.DataFrame({
        "station_name": raw["名称"].astype(str).str.strip(),
        "province": raw["province"],
        "city": raw["city"],
        "address": raw["地址"].astype(str).str.strip(),
        "fast_piles": raw["fast_piles"],
        "slow_piles": raw["slow_piles"],
        "total_piles": raw["total_piles"],
        "electricity_price": raw["electricity_price"].round(3),
        "service_price": raw["service_price"].round(3),
        "total_price": raw["total_price"],
        "parking_free": raw["parking_free"],
        "open_24h": raw["open_24h"],
        "scale_level": raw["scale_level"],
    })
    out.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
    CREATE TABLE charging_stations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        station_name TEXT NOT NULL,
        province TEXT NOT NULL,
        city TEXT NOT NULL,
        address TEXT NOT NULL,
        fast_piles INTEGER NOT NULL,
        slow_piles INTEGER NOT NULL,
        total_piles INTEGER NOT NULL,
        electricity_price REAL,
        service_price REAL,
        total_price REAL,
        parking_free INTEGER NOT NULL,
        open_24h INTEGER NOT NULL,
        scale_level TEXT NOT NULL
    );
    CREATE INDEX idx_province ON charging_stations(province);
    CREATE INDEX idx_city ON charging_stations(city);
    CREATE INDEX idx_scale ON charging_stations(scale_level);
    """)
    out.to_sql("charging_stations", conn, if_exists="append", index=False)
    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM charging_stations").fetchone()[0]
    conn.close()

    report["cleaned_rows"] = int(total)
    report["provinces"] = int(out["province"].nunique())
    report["cities"] = int(out["city"].nunique())
    report["total_fast_piles"] = int(out["fast_piles"].sum())
    report["total_slow_piles"] = int(out["slow_piles"].sum())
    with open(REPORT_PATH, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("已生成:", DB_PATH)
    print("已生成:", CSV_PATH)


if __name__ == "__main__":
    main()
