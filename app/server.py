# -*- coding: utf-8 -*-
"""
server.py
全国新能源汽车充电基础设施运营态势大屏 · Flask 后端
数据表：charging_stations（由 database/clean_dataset.py 从公开数据清洗生成）
所有统计均在 SQLite 中用 SQL 聚合完成，接口只返回聚合结果。
"""
import os
import sqlite3

from flask import Flask, jsonify, render_template, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
DB_PATH = os.path.join(PROJECT_DIR, "database", "analytics.db")

app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, "templates"),
            static_folder=os.path.join(BASE_DIR, "static"))


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def query(sql, params=()):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return cursor.fetchall()
    finally:
        conn.close()


def province_where(province):
    """返回 (where 子句, 参数列表)，省份用占位符传入，避免 SQL 拼接注入。"""
    if province:
        return " WHERE province = ?", [province]
    return "", []


@app.errorhandler(Exception)
def handle_error(exc):
    app.logger.exception("接口异常")
    return jsonify({"code": 500, "message": str(exc)}), 500


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/favicon.ico")
def favicon():
    return "", 204


@app.route("/api/kpi")
def get_kpi():
    province = request.args.get("province", "").strip()
    where, params = province_where(province)
    rows = query(f"""
        SELECT COUNT(*) AS station_count,
               COALESCE(SUM(fast_piles), 0) AS fast_piles,
               COALESCE(SUM(slow_piles), 0) AS slow_piles,
               COUNT(DISTINCT city) AS city_count,
               ROUND(AVG(electricity_price), 3) AS avg_electricity,
               ROUND(AVG(service_price), 3) AS avg_service,
               ROUND(AVG(total_price), 3) AS avg_total,
               COUNT(DISTINCT province) AS province_count
        FROM charging_stations{where}
    """, params)
    return jsonify({"code": 0, "data": dict(rows[0])})


@app.route("/api/map-data")
def get_map_data():
    rows = query("""
        SELECT province,
               COUNT(*) AS value,
               SUM(fast_piles) AS fast_piles,
               SUM(slow_piles) AS slow_piles,
               ROUND(AVG(electricity_price), 3) AS avg_electricity
        FROM charging_stations
        GROUP BY province
        ORDER BY value DESC
    """)
    return jsonify({"code": 0, "data": [dict(r) for r in rows]})


@app.route("/api/city-top")
def get_city_top():
    province = request.args.get("province", "").strip()
    where, params = province_where(province)
    where = (where + " AND city <> '未知'") if where else " WHERE city <> '未知'"
    rows = query(f"""
        SELECT city, COUNT(*) AS value, SUM(fast_piles) AS fast_piles
        FROM charging_stations{where}
        GROUP BY city
        ORDER BY value DESC
        LIMIT 10
    """, params)
    return jsonify({"code": 0, "data": [dict(r) for r in rows]})


@app.route("/api/scale-dist")
def get_scale_dist():
    province = request.args.get("province", "").strip()
    where, params = province_where(province)
    rows = query(f"""
        SELECT scale_level AS name,
               COUNT(*) AS value,
               SUM(total_piles) AS piles
        FROM charging_stations{where}
        GROUP BY scale_level
    """, params)
    order = {"小型站(1-5桩)": 0, "中型站(6-10桩)": 1, "大型站(11-20桩)": 2, "超大型站(20桩以上)": 3}
    data = sorted((dict(r) for r in rows), key=lambda x: order.get(x["name"], 9))
    return jsonify({"code": 0, "data": data})


@app.route("/api/pile-structure")
def get_pile_structure():
    province = request.args.get("province", "").strip()
    where, params = province_where(province)
    rows = query(f"""
        SELECT COALESCE(SUM(fast_piles), 0) AS fast,
               COALESCE(SUM(slow_piles), 0) AS slow
        FROM charging_stations{where}
    """, params)
    row = rows[0]
    data = [{"name": "快充桩", "value": row["fast"]}, {"name": "慢充桩", "value": row["slow"]}]
    return jsonify({"code": 0, "data": data})


@app.route("/api/price-dist")
def get_price_dist():
    province = request.args.get("province", "").strip()
    where, params = province_where(province)
    rows = query(f"""
        SELECT CASE
                   WHEN electricity_price < 0.6 THEN '0.6元以下'
                   WHEN electricity_price < 0.8 THEN '0.6-0.8元'
                   WHEN electricity_price < 1.0 THEN '0.8-1.0元'
                   WHEN electricity_price < 1.2 THEN '1.0-1.2元'
                   ELSE '1.2元以上'
               END AS name,
               COUNT(*) AS value
        FROM charging_stations{where}
        GROUP BY name
    """, params)
    order = {"0.6元以下": 0, "0.6-0.8元": 1, "0.8-1.0元": 2, "1.0-1.2元": 3, "1.2元以上": 4}
    data = sorted((dict(r) for r in rows), key=lambda x: order.get(x["name"], 9))
    return jsonify({"code": 0, "data": data})


@app.route("/api/station-feed")
def get_station_feed():
    province = request.args.get("province", "").strip()
    where, params = province_where(province)
    rows = query(f"""
        SELECT station_name, province, city, fast_piles, slow_piles,
               electricity_price, service_price, parking_free, open_24h
        FROM charging_stations{where}
        ORDER BY RANDOM()
        LIMIT 6
    """, params)
    return jsonify({"code": 0, "data": [dict(r) for r in rows]})


if __name__ == "__main__":
    print("=" * 64)
    print("充电基础设施运营态势大屏已启动：http://127.0.0.1:8080")
    print("=" * 64)
    app.run(host="0.0.0.0", port=8080, debug=False)
