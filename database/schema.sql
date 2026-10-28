-- 全国充电站数据表结构（由 database/clean_dataset.py 执行，此处保留供查看）
DROP TABLE IF EXISTS charging_stations;

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
