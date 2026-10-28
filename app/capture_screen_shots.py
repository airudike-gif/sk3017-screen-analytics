# -*- coding: utf-8 -*-
"""
capture_screen_shots.py
用 Selenium + 无头 Chrome 在 1920×1080 下截取大屏的默认视图与下钻视图。
运行前先启动服务：python app/server.py
"""
import os
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

BASE_URL = "http://127.0.0.1:8080"
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOT_DIR = os.path.join(PROJECT_DIR, "screenshots")
os.makedirs(SHOT_DIR, exist_ok=True)


def build_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--hide-scrollbars")
    options.add_argument("--force-device-scale-factor=1")
    return webdriver.Chrome(options=options)


def main():
    driver = build_driver()
    try:
        driver.set_window_size(1920, 1080)
        # 用 CDP 把视口精确锁定为 1920×1080，截图不带浏览器边框
        driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
            "width": 1920, "height": 1080, "deviceScaleFactor": 1, "mobile": False
        })

        driver.get(BASE_URL)
        time.sleep(5)  # 等 ECharts 完成渲染
        full = os.path.join(SHOT_DIR, "01_dashboard_full_view.png")
        driver.save_screenshot(full)
        print("已保存:", full)

        driver.get(BASE_URL + "/?province=%E5%B9%BF%E4%B8%9C%E7%9C%81")
        time.sleep(5)
        drill = os.path.join(SHOT_DIR, "02_dashboard_drilldown_view.png")
        driver.save_screenshot(drill)
        print("已保存:", drill)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
