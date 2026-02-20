"use client";

import { useQuantRankings, useWhaleTop, useSectorRanking, usePipelineStatus } from "@/lib/queries";
import { formatKRW, formatPercent, formatLargeNumber } from "@/lib/utils";
import Link from "next/link";

function StatCard({ title, value, subtitle }: { title: string; value: string; subtitle?: string }) {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-5">
      <h3 className="text-sm font-medium text-slate-500">{title}</h3>
      <p className="text-2xl font-bold text-slate-900 mt-1">{value}</p>
      {subtitle && <p className="text-xs text-slate-400 mt-1">{subtitle}</p>}
    </div>
  );
}

function SectionHeader({ title, href }: { title: string; href: string }) {
  return (
    <div className="flex items-center justify-between mb-3">
      <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
      <Link href={href} className="text-sm text-whale-600 hover:text-whale-700">
        더보기 →
      </Link>
    </div>
  );
}

export default function DashboardPage() {
  const { data: quantData } = useQuantRankings({ size: 10 });
  const { data: whaleData } = useWhaleTop({ size: 10 });
  const { data: sectorData } = useSectorRanking();
  const { data: pipelineData } = usePipelineStatus();

  const topStocks = quantData?.data || [];
  const topWhales = whaleData?.data || [];
  const sectors = sectorData?.data || [];
  const collections = pipelineData?.data?.collections || [];

  const lastCollection = collections.length > 0
    ? collections.reduce((a: any, b: any) => (a.completed_at > b.completed_at ? a : b))
    : null;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">대시보드</h1>
        <p className="text-slate-500 mt-1">한국 주식 시장 분석 - KOSPI/KOSDAQ</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="분석 종목"
          value={String(quantData?.meta?.total || "-")}
          subtitle="퀀트 분석 완료"
        />
        <StatCard
          title="고래 매집 종목"
          value={String(whaleData?.meta?.total || "-")}
          subtitle="Whale Score 기준"
        />
        <StatCard
          title="추적 섹터"
          value={String(sectors.length || "-")}
          subtitle="KOSPI + KOSDAQ"
        />
        <StatCard
          title="최근 수집"
          value={lastCollection?.target_date || "-"}
          subtitle={lastCollection?.status === "success" ? "성공" : "확인 필요"}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Quant Picks */}
        <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-5">
          <SectionHeader title="퀀트 분석 TOP 10" href="/analysis/quant" />
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-500 border-b">
                  <th className="text-left py-2">종목</th>
                  <th className="text-center py-2">등급</th>
                  <th className="text-center py-2">F-Score</th>
                  <th className="text-right py-2">안전마진</th>
                </tr>
              </thead>
              <tbody>
                {topStocks.map((stock: any) => (
                  <tr key={stock.ticker} className="border-b border-slate-50 hover:bg-slate-50">
                    <td className="py-2">
                      <Link href={`/stocks/${stock.ticker}`} className="hover:text-whale-600">
                        <span className="font-medium">{stock.name}</span>
                        <span className="text-slate-400 text-xs ml-1">{stock.ticker}</span>
                      </Link>
                    </td>
                    <td className="text-center">
                      <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${
                        stock.investment_grade?.startsWith("A") ? "bg-green-100 text-green-700" :
                        stock.investment_grade?.startsWith("B") ? "bg-blue-100 text-blue-700" :
                        "bg-slate-100 text-slate-600"
                      }`}>
                        {stock.investment_grade || "-"}
                      </span>
                    </td>
                    <td className="text-center">{stock.fscore ?? "-"}/9</td>
                    <td className="text-right">{formatPercent(stock.safety_margin)}</td>
                  </tr>
                ))}
                {topStocks.length === 0 && (
                  <tr><td colSpan={4} className="py-4 text-center text-slate-400">데이터 없음</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Top Whale Picks */}
        <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-5">
          <SectionHeader title="고래 매집 TOP 10" href="/analysis/whale" />
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-500 border-b">
                  <th className="text-left py-2">종목</th>
                  <th className="text-center py-2">신호</th>
                  <th className="text-right py-2">Whale Score</th>
                </tr>
              </thead>
              <tbody>
                {topWhales.map((stock: any) => (
                  <tr key={stock.ticker} className="border-b border-slate-50 hover:bg-slate-50">
                    <td className="py-2">
                      <Link href={`/stocks/${stock.ticker}`} className="hover:text-whale-600">
                        <span className="font-medium">{stock.name}</span>
                        <span className="text-slate-400 text-xs ml-1">{stock.ticker}</span>
                      </Link>
                    </td>
                    <td className="text-center">
                      <span className={`inline-block px-2 py-0.5 rounded text-xs ${
                        stock.signal === "strong_accumulation" ? "bg-red-100 text-red-700" :
                        stock.signal === "mild_accumulation" ? "bg-orange-100 text-orange-700" :
                        "bg-slate-100 text-slate-600"
                      }`}>
                        {stock.signal === "strong_accumulation" ? "강한매집" :
                         stock.signal === "mild_accumulation" ? "완만매집" :
                         stock.signal === "distribution" ? "매도우위" : "중립"}
                      </span>
                    </td>
                    <td className="text-right font-medium">{stock.whale_score?.toFixed(1) ?? "-"}</td>
                  </tr>
                ))}
                {topWhales.length === 0 && (
                  <tr><td colSpan={3} className="py-4 text-center text-slate-400">데이터 없음</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Sector Overview */}
      <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-5">
        <SectionHeader title="섹터 랭킹" href="/analysis/trend" />
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
          {sectors.slice(0, 10).map((sector: any, idx: number) => (
            <Link
              key={sector.sector}
              href={`/analysis/trend`}
              className="p-3 rounded-lg border border-slate-100 hover:border-whale-200 hover:bg-whale-50 transition-colors"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">#{idx + 1}</span>
                <span className="text-xs text-slate-400">{sector.stock_count}종목</span>
              </div>
              <p className="font-medium text-sm mt-1 truncate">{sector.sector}</p>
              <p className={`text-xs mt-0.5 ${
                (sector.avg_rs_20d || 0) >= 1 ? "text-red-500" : "text-blue-500"
              }`}>
                RS {sector.avg_rs_20d?.toFixed(3) || "-"}
              </p>
            </Link>
          ))}
          {sectors.length === 0 && (
            <p className="col-span-full text-center text-slate-400 py-4">섹터 데이터 없음</p>
          )}
        </div>
      </div>
    </div>
  );
}
