"use client";

import ReactECharts from "echarts-for-react";

interface LineChartProps {
  series: { name: string; data: number[]; color?: string }[];
  xLabels: string[];
  height?: number;
  yAxisName?: string;
}

export function LineChart({ series, xLabels, height = 300, yAxisName }: LineChartProps) {
  const option = {
    tooltip: { trigger: "axis" },
    legend: { bottom: 0, textStyle: { fontSize: 11 } },
    grid: { left: "8%", right: "4%", top: "8%", bottom: "12%" },
    xAxis: { type: "category", data: xLabels, axisLabel: { fontSize: 10 } },
    yAxis: { type: "value", name: yAxisName, scale: true, splitLine: { lineStyle: { color: "#f1f5f9" } } },
    series: series.map((s) => ({
      name: s.name,
      type: "line",
      data: s.data,
      smooth: true,
      lineStyle: { width: 2, color: s.color },
      itemStyle: { color: s.color },
      symbol: "none",
    })),
  };

  return <ReactECharts option={option} style={{ height }} />;
}
