# 课程设计选题：题目六-数据可视化大屏（全国新能源汽车充电基础设施运营态势大屏）

本项目是 SK3017《Python Web企业级项目开发》课程设计，采用“题库选题 + AI 编程助手协作”的方式完成。数据来自公开的全国充电站信息数据集，Flask 在服务端用 SQL 完成聚合统计，前端用 ECharts 做深色大屏，支持点击省份下钻联动。

## 一、数据集来源

- 原始数据仓库：<https://github.com/xjtulyc/Electric_Vehicle_Crawler>
- 数据目录：仓库中的 `crawler/充电桩/`，按省级行政区存放 33 个 `xlsx` 文件
- 字段：站点名称、地址、快充数量、慢充数量、支付方式、充电费、服务费、停车费、开放时间
- 规模：原始 34,186 条站点记录，覆盖 31 个省级行政区、633 个城市
- 许可与用途：仓库公开可访问，数据用于课程设计的数据处理与可视化练习；报告中已注明来源

## 二、清洗流程

清洗脚本为 `database/clean_dataset.py`，读取 `data_raw/*.xlsx`，处理步骤和结果如下（完整统计见 `docs/cleaning_report.json`）：

1. **字段解析**：从地址中解析省、市；从“充电费/服务费”文本中解析分时段价格并取均值（原始数据有 5 种写法）；从停车费文本判断是否免费；从开放时间判断是否 24 小时。
2. **去重**：按“站点名称 + 地址”去重，删除 63 条重复记录。
3. **无效与异常剔除**：快充、慢充都为 0，或单项超过 500 个的明显录入异常记录，共删除 471 条。
4. **异常价格处理**：电费小于等于 0 或大于 3 元/度的记录视为异常，置为空值，共 889 条。
5. **缺失值填充**：价格缺失用同省中位数填充（电费 1,798 条、服务费 7,173 条）；地址解析不出城市的记录保留，城市记为“未知”，不参与城市排行。

清洗后入库 **33,652 条**，合计快充桩 309,180 个、慢充桩 36,440 个。

## 三、项目结构

```text
sk3017-screen-analytics/
├── app/
│   ├── static/
│   │   ├── css/screen.css          # 深色大屏样式（1920×1080 固定画布 + 自适应缩放）
│   │   └── js/
│   │       ├── china.json          # 本地中国地图 GeoJSON
│   │       ├── echarts.min.js      # 本地 ECharts 运行时
│   │       └── screen_engine.js    # 图表渲染与省份下钻联动
│   ├── templates/index.html        # 大屏主页面
│   ├── capture_screen_shots.py     # Selenium 截图脚本（1920×1080）
│   └── server.py                   # Flask 后端（SQL 聚合接口）
├── database/
│   ├── analytics.db                # 清洗后生成的 SQLite 数据库
│   ├── clean_dataset.py            # 数据清洗与入库脚本
│   └── schema.sql                  # 表结构（由清洗脚本生成）
├── data_raw/                       # 原始省级 xlsx 文件（数据来源见第一节）
├── data/charging_stations.csv      # 清洗后的 CSV 导出
├── docs/
│   ├── 设计文档.md                  # 数据集、字段、清洗策略、图表聚合逻辑
│   ├── DEVELOPMENT_LOG.md          # 开发日志
│   ├── DEBUG_LOG.md                # Debug 日志
│   ├── AI协作记录.md               # AI 提示词与采纳过程
│   └── cleaning_report.json        # 清洗统计
├── screenshots/                    # 1920×1080 运行截图（默认视图 / 下钻视图）
├── requirements.txt
└── README.md
```

## 四、运行方式

建议 Python 3.10 / 3.11，先安装依赖：

```bash
pip install -r requirements.txt
```

本项目在 Windows 下用 Anaconda 环境验证（Python 3.13 + Flask 2.3.3 + pandas 2.2 也可运行）。

1）重建数据库（仓库内已带生成好的 `database/analytics.db`，可跳过）：

```bash
# 若 data_raw 为空，先从第一节的数据仓库下载 33 个 xlsx 到 data_raw/
python database/clean_dataset.py
```

2）启动大屏服务：

```bash
python app/server.py
```

浏览器访问 <http://127.0.0.1:8080>。项目没有登录功能，不需要测试账号。

3）重新生成截图（需先启动服务）：

```bash
python app/capture_screen_shots.py
```

## 五、功能与图表

- 6 个顶部指标卡：充电站总数、快充桩总数、慢充桩总数、覆盖城市数、平均电费、平均服务费
- 5 个 ECharts 图表：全国各省充电站数量地图、站点规模分布环形图、快充/慢充桩结构玫瑰图、城市车站数量 TOP10、电费区间分布
- 下钻联动：点击地图上的省份，指标卡与 4 个图表同时切换到该省数据，右上角可一键重置
- 底部站点明细列表：每 8 秒随机抽取 6 条站点刷新

所有统计都在 SQLite 中用 SQL 聚合（COUNT/SUM/AVG/GROUP BY/CASE WHEN）完成，前端只负责渲染。

## 六、接口清单

| 接口 | 说明 |
| --- | --- |
| `/api/kpi` | 6 个指标卡聚合，支持 `?province=` |
| `/api/map-data` | 各省充电站数、快慢充桩数、平均电费 |
| `/api/city-top` | 城市充电站数 TOP10，支持 `?province=` |
| `/api/scale-dist` | 站点规模分档统计，支持 `?province=` |
| `/api/pile-structure` | 快充/慢充桩数量，支持 `?province=` |
| `/api/price-dist` | 电费区间分布，支持 `?province=` |
| `/api/station-feed` | 站点明细抽样（6 条） |

## 七、说明

- 数据为公开仓库中的站点信息，可能存在采集时间较早、个别字段缺失的情况，清洗策略见第二节。
- 大屏按 1920×1080 设计，页面在其它分辨率下会等比缩放，不会出现滚动条。
