"use client";

import ReactECharts from "echarts-for-react";
import type { PriceData } from "@/types/api";

interface CandlestickChartProps {
  data: PriceData[];
  height?: number;
}

export function CandlestickChart({ data, height = 400 }: CandlestickChartProps) {
  if (!data.length) return <div className="flex items-center justify-center h-64 text-slate-400">데이터 없음</div>;

  const dates = data.map((d) => d.trade_date);
  const ohlc = data.map((d) => [d.open ?? d.close, d.close, d.low ?? d.close, d.high ?? d.close]);
  const volumes = data.map((d) => d.volume);

  const option = {
    tooltip: { trigger: "axis", axisPointer: { type: "cross" } },
    grid: [
      { left: "8%", right: "4%", top: "8%", height: "55%" },
      { left: "8%", right: "4%", top: "70%", height: "20%" },
    ],
    xAxis: [
      { type: "category", data: dates, gridIndex: 0, axisLabel: { show: false } },
      { type: "category", data: dates, gridIndex: 1, axisLabel: { fontSize: 10 } },
    ],
    yAxis: [
      { type: "value", gridIndex: 0, scale: true, splitLine: { lineStyle: { color: "#f1f5f9" } } },
      { type: "value", gridIndex: 1, splitLine: { show: false }, axisLabel: { show: false } },
    ],
    series: [
      {
        type: "candlestick",
        data: ohlc,
        xAxisIndex: 0,
        yAxisIndex: 0,
        itemStyle: {
          color: "#ef4444",
          color0: "#3b82f6",
          borderColor: "#ef4444",
          borderColor0: "#3b82f6",
        },
      },
      {
        type: "bar",
        data: volumes,
        xAxisIndex: 1,
        yAxisIndex: 1,
        itemStyle: { color: "#94a3b8" },
      },
    ],
    dataZoom: [{ type: "inside", xAxisIndex: [0, 1], start: 60, end: 100 }],
  };

  return <ReactECharts option={option} style={{ height }} />;
}
