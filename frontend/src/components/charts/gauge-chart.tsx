"use client";

import ReactECharts from "echarts-for-react";

interface GaugeChartProps {
  value: number;
  max?: number;
  label: string;
  color?: string;
  height?: number;
}

export function GaugeChart({ value, max = 100, label, color = "#0c93e7", height = 200 }: GaugeChartProps) {
  const option = {
    series: [
      {
        type: "gauge",
        startAngle: 200,
        endAngle: -20,
        min: 0,
        max,
        pointer: { show: false },
        progress: {
          show: true,
          width: 12,
          roundCap: true,
          itemStyle: { color },
        },
        axisLine: { lineStyle: { width: 12, color: [[1, "#e2e8f0"]] } },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        detail: {
          valueAnimation: true,
          fontSize: 24,
          fontWeight: "bold",
          color: "#1e293b",
          offsetCenter: [0, "20%"],
          formatter: `{value}`,
        },
        title: {
          offsetCenter: [0, "50%"],
          fontSize: 12,
          color: "#64748b",
        },
        data: [{ value, name: label }],
      },
    ],
  };

  return <ReactECharts option={option} style={{ height }} />;
}
