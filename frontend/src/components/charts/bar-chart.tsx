"use client";

import ReactECharts from "echarts-for-react";

interface BarChartProps {
  labels: string[];
  series: { name: string; data: number[]; color?: string }[];
  height?: number;
  horizontal?: boolean;
  stacked?: boolean;
}

export function BarChart({ labels, series, height = 300, horizontal = false, stacked = false }: BarChartProps) {
  const categoryAxis = { type: "category" as const, data: labels, axisLabel: { fontSize: 10 } };
  const valueAxis = { type: "value" as const, splitLine: { lineStyle: { color: "#f1f5f9" } } };

  const option = {
    tooltip: { trigger: "axis" },
    legend: series.length > 1 ? { bottom: 0, textStyle: { fontSize: 11 } } : undefined,
    grid: { left: horizontal ? "20%" : "8%", right: "4%", top: "8%", bottom: series.length > 1 ? "12%" : "8%" },
    xAxis: horizontal ? valueAxis : categoryAxis,
    yAxis: horizontal ? categoryAxis : valueAxis,
    series: series.map((s) => ({
      name: s.name,
      type: "bar",
      data: s.data.map((v) => ({
        value: v,
        itemStyle: {
          color: s.color,
          borderRadius: horizontal
            ? (v >= 0 ? [0, 4, 4, 0] : [4, 0, 0, 4])
            : (v >= 0 ? [4, 4, 0, 0] : [0, 0, 4, 4]),
        },
      })),
      stack: stacked ? "total" : undefined,
      barMaxWidth: 40,
    })),
  };

  return <ReactECharts option={option} style={{ height }} />;
}
