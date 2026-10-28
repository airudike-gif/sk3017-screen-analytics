/**
 * screen_engine.js
 * 全国充电基础设施运营态势大屏：图表渲染 + 省级下钻联动
 * 数据源：/api/*（后端 SQLite 聚合，见 app/server.py）
 */

let currentProvince = "";
const charts = {};

// ---------------------------------------------------------------- 基础工具
async function fetchJson(url) {
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error("HTTP " + res.status);
    return await res.json();
  } catch (err) {
    console.error("接口请求失败:", url, err);
    return { code: -1, data: [] };
  }
}

// 统一管理图表实例：已存在则复用，避免重复 init 造成实例泄漏
function getChart(id) {
  const dom = document.getElementById(id);
  if (!charts[id]) {
    charts[id] = echarts.init(dom);
  }
  return charts[id];
}

function withProvince(path) {
  if (!currentProvince) return path;
  const sep = path.indexOf("?") >= 0 ? "&" : "?";
  return path + sep + "province=" + encodeURIComponent(currentProvince);
}

function startClock() {
  function update() {
    const now = new Date();
    document.getElementById("currentTime").innerText = now.toTimeString().split(" ")[0];
    document.getElementById("currentDate").innerText = now.toLocaleDateString("zh-CN", {
      year: "numeric", month: "2-digit", day: "2-digit", weekday: "short"
    });
  }
  update();
  setInterval(update, 1000);
}

// 以 1920×1080 为设计画布，按窗口大小等比缩放并居中，保证大屏一屏完整展示
function fitScreen() {
  const stage = document.getElementById("screen-stage");
  const scale = Math.min(window.innerWidth / 1920, window.innerHeight / 1080);
  const offsetX = (window.innerWidth - 1920 * scale) / 2;
  const offsetY = (window.innerHeight - 1080 * scale) / 2;
  stage.style.transform = `translate(${offsetX}px, ${offsetY}px) scale(${scale})`;
}

// ---------------------------------------------------------------- 顶部指标
async function loadKpi() {
  const res = await fetchJson(withProvince("/api/kpi"));
  if (res.code !== 0) return;
  const d = res.data;
  document.getElementById("kpi_total").innerText = Number(d.station_count).toLocaleString();
  document.getElementById("kpi_fast").innerText = Number(d.fast_piles).toLocaleString();
  document.getElementById("kpi_slow").innerText = Number(d.slow_piles).toLocaleString();
  document.getElementById("kpi_city").innerText = d.city_count;
  document.getElementById("kpi_price").innerText = Number(d.avg_electricity).toFixed(2);
  document.getElementById("kpi_service").innerText = Number(d.avg_service).toFixed(2);
  document.getElementById("kpi_fast_sub").innerText =
    "占充电桩 " + (100 * d.fast_piles / Math.max(1, d.fast_piles + d.slow_piles)).toFixed(1) + "%";
  document.getElementById("kpi_city_sub").innerText =
    "平均每市 " + Math.round(d.station_count / Math.max(1, d.city_count)) + " 座站点";
}

// ---------------------------------------------------------------- 省级热力地图
async function initMapChart() {
  const geoJson = await fetchJson("/static/js/china.json");
  echarts.registerMap("china", geoJson);
  const res = await fetchJson("/api/map-data");
  const data = (res.data || []).map(d => Object.assign({}, d, { name: d.province }));
  const maxValue = Math.max.apply(null, data.map(d => d.value));

  const chart = getChart("chart_map");
  chart.setOption({
    tooltip: {
      trigger: "item",
      backgroundColor: "rgba(15, 23, 42, 0.9)",
      borderColor: "rgba(56, 189, 248, 0.4)",
      borderWidth: 1,
      textStyle: { color: "#f8fafc", fontSize: 12 },
      formatter: function (p) {
        if (!p.data) return p.name + "<br/>暂无接入数据";
        return `<div style="font-weight:bold;color:#38bdf8;margin-bottom:4px;">${p.name}</div>
          <div>充电站：<span style="color:#fff;font-weight:600;">${p.data.value}</span> 座</div>
          <div>快充桩：<span style="color:#06b6d4;">${p.data.fast_piles}</span> 个</div>
          <div>慢充桩：<span style="color:#10b981;">${p.data.slow_piles}</span> 个</div>
          <div>平均电费：<span style="color:#fbbf24;">${p.data.avg_electricity}</span> 元/度</div>`;
      }
    },
    visualMap: {
      min: 0,
      max: maxValue,
      left: 20,
      bottom: 20,
      text: ["站点多", "站点少"],
      realtime: false,
      calculable: true,
      inRange: { color: ["#0f2b48", "#0284c7", "#06b6d4", "#38bdf8"] },
      textStyle: { color: "#94a3b8", fontSize: 11 }
    },
    series: [{
      name: "各省充电站数量",
      type: "map",
      map: "china",
      roam: true,
      zoom: 1.18,
      label: { show: false, color: "#cbd5e1", fontSize: 10 },
      itemStyle: {
        areaColor: "#0d1b2a",
        borderColor: "rgba(56, 189, 248, 0.35)",
        borderWidth: 1,
        shadowColor: "rgba(0, 0, 0, 0.5)",
        shadowBlur: 15
      },
      emphasis: {
        itemStyle: {
          areaColor: "#0284c7",
          borderColor: "#38bdf8",
          borderWidth: 1.5,
          shadowBlur: 20
        },
        label: { show: true, color: "#ffffff", fontWeight: "bold" }
      },
      data: data
    }]
  });

  chart.off("click");
  chart.on("click", function (params) {
    if (params.name) setFilterProvince(params.name);
  });
}

// ---------------------------------------------------------------- 站点规模分布
async function initScaleChart() {
  const res = await fetchJson(withProvince("/api/scale-dist"));
  const chart = getChart("chart_brand");
  chart.setOption({
    tooltip: {
      trigger: "item",
      backgroundColor: "rgba(15, 23, 42, 0.9)",
      borderColor: "rgba(56, 189, 248, 0.4)",
      formatter: "{b}: {c} 座 ({d}%)"
    },
    legend: {
      orient: "vertical",
      right: 10,
      top: "middle",
      textStyle: { color: "#94a3b8", fontSize: 11 },
      itemWidth: 10,
      itemHeight: 10
    },
    color: ["#06b6d4", "#38bdf8", "#6366f1", "#8b5cf6"],
    series: [{
      name: "站点规模",
      type: "pie",
      radius: ["45%", "72%"],
      center: ["40%", "50%"],
      itemStyle: { borderRadius: 6, borderColor: "#070c18", borderWidth: 2 },
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 13, fontWeight: "bold", color: "#fff" } },
      data: res.data
    }]
  }, true);
}

// ---------------------------------------------------------------- 快慢充结构
async function initPileChart() {
  const res = await fetchJson(withProvince("/api/pile-structure"));
  const chart = getChart("chart_battery");
  chart.setOption({
    tooltip: {
      trigger: "item",
      backgroundColor: "rgba(15, 23, 42, 0.9)",
      borderColor: "rgba(56, 189, 248, 0.4)",
      formatter: "{b}: {c} 个 ({d}%)"
    },
    series: [{
      name: "充电桩类型",
      type: "pie",
      radius: ["25%", "72%"],
      center: ["50%", "50%"],
      roseType: "radius",
      itemStyle: { borderRadius: 5, borderColor: "#070c18", borderWidth: 1.5 },
      label: { color: "#94a3b8", fontSize: 11, formatter: "{b}\n{c} 个" },
      color: ["#06b6d4", "#10b981"],
      data: res.data
    }]
  }, true);
}

// ---------------------------------------------------------------- 城市 TOP10
async function initCityChart() {
  const res = await fetchJson(withProvince("/api/city-top"));
  const data = (res.data || []).slice().reverse();
  const chart = getChart("chart_trend");
  chart.setOption({
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      backgroundColor: "rgba(15, 23, 42, 0.9)",
      borderColor: "rgba(56, 189, 248, 0.4)"
    },
    grid: { left: "3%", right: "6%", bottom: "3%", top: "6%", containLabel: true },
    xAxis: {
      type: "value",
      splitLine: { lineStyle: { color: "rgba(148, 163, 184, 0.08)" } },
      axisLabel: { color: "#94a3b8", fontSize: 11 }
    },
    yAxis: {
      type: "category",
      data: data.map(d => d.city),
      axisLine: { lineStyle: { color: "rgba(148, 163, 184, 0.2)" } },
      axisLabel: { color: "#94a3b8", fontSize: 11 }
    },
    series: [{
      type: "bar",
      data: data.map(d => d.value),
      barWidth: "55%",
      itemStyle: {
        borderRadius: [0, 4, 4, 0],
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: "#1e3a8a" },
          { offset: 1, color: "#38bdf8" }
        ])
      }
    }]
  }, true);
}

// ---------------------------------------------------------------- 电费区间分布
async function initPriceChart() {
  const res = await fetchJson(withProvince("/api/price-dist"));
  const data = res.data || [];
  const chart = getChart("chart_power");
  chart.setOption({
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(15, 23, 42, 0.9)",
      borderColor: "rgba(56, 189, 248, 0.4)"
    },
    grid: { left: "3%", right: "4%", bottom: "6%", top: "15%", containLabel: true },
    xAxis: {
      type: "category",
      data: data.map(i => i.name),
      axisLabel: { color: "#94a3b8", fontSize: 10, rotate: 10 },
      axisLine: { lineStyle: { color: "rgba(148, 163, 184, 0.2)" } }
    },
    yAxis: {
      type: "value",
      splitLine: { lineStyle: { color: "rgba(148, 163, 184, 0.08)" } },
      axisLabel: { color: "#94a3b8" }
    },
    series: [{
      type: "bar",
      data: data.map(i => i.value),
      barWidth: "40%",
      itemStyle: {
        borderRadius: [4, 4, 0, 0],
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: "#06b6d4" },
          { offset: 1, color: "#1e3a8a" }
        ])
      }
    }]
  }, true);
}

// ---------------------------------------------------------------- 站点滚动列表
async function loadStationFeed() {
  const res = await fetchJson(withProvince("/api/station-feed"));
  if (res.code !== 0) return;
  const tbody = document.getElementById("telemetry_body");
  tbody.innerHTML = "";
  res.data.forEach(r => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td style="color:#f1f5f9;font-weight:600;">${r.station_name}</td>
      <td><span style="color:#38bdf8;">${r.province}</span> · ${r.city}</td>
      <td>${r.fast_piles} / ${r.slow_piles}</td>
      <td>${Number(r.electricity_price).toFixed(2)} 元/度</td>
      <td>${Number(r.service_price).toFixed(2)} 元/度</td>
      <td><span class="status-badge ${r.parking_free ? 'status-normal' : 'status-warn'}">${r.parking_free ? '免费停车' : '停车收费'}</span></td>
      <td><span class="status-badge ${r.open_24h ? 'status-normal' : 'status-warn'}">${r.open_24h ? '24 小时' : '限时开放'}</span></td>
    `;
    tbody.appendChild(tr);
  });
}

// ---------------------------------------------------------------- 下钻联动
function setFilterProvince(provinceName) {
  currentProvince = provinceName || "";
  document.getElementById("activeFilterText").innerText =
    currentProvince || "全国视图 (全量 33,652 座站点)";
  document.getElementById("resetFilterBtn").style.display = currentProvince ? "inline-block" : "none";

  loadKpi();
  initScaleChart();
  initPileChart();
  initCityChart();
  initPriceChart();
  loadStationFeed();
}

function resetFilter() {
  setFilterProvince("");
}

// 窗口自适应：先按 1920×1080 重算画布缩放，再让图表跟着容器重排（150ms 防抖）
let resizeTimer = null;
window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    fitScreen();
    Object.keys(charts).forEach(key => charts[key] && charts[key].resize());
  }, 150);
});

document.addEventListener("DOMContentLoaded", async () => {
  fitScreen();
  startClock();
  await initMapChart();
  await initScaleChart();
  await initPileChart();
  await initCityChart();
  await initPriceChart();
  await loadKpi();
  await loadStationFeed();
  setInterval(loadStationFeed, 8000);

  // 支持直接带省份参数打开（例如 /?province=广东省），方便演示和自动截图
  const preset = new URLSearchParams(window.location.search).get("province");
  if (preset) {
    setFilterProvince(preset);
  }
});
