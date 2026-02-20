"use client";

import { useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useStocks } from "@/lib/queries";
import { formatKRW, formatPercent } from "@/lib/utils";

export default function StocksPage() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const market = searchParams.get("market") || "";
  const search = searchParams.get("search") || "";
  const page = Number(searchParams.get("page") || "1");

  const [searchInput, setSearchInput] = useState(search);

  const { data, isLoading } = useStocks({
    market: market || undefined,
    search: search || undefined,
    page,
    size: 50,
  });

  const stocks = data?.data || [];
  const total = data?.meta?.total || 0;
  const totalPages = Math.ceil(total / 50);

  function updateParams(updates: Record<string, string>) {
    const params = new URLSearchParams(searchParams.toString());
    Object.entries(updates).forEach(([k, v]) => {
      if (v) params.set(k, v);
      else params.delete(k);
    });
    if (updates.search !== undefined || updates.market !== undefined) {
      params.set("page", "1");
    }
    router.push(`/stocks?${params.toString()}`);
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-slate-900">종목 스크리너</h1>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-4">
        <div className="flex flex-wrap gap-3 items-center">
          {/* Search */}
          <div className="flex-1 min-w-[200px]">
            <input
              type="text"
              placeholder="종목명 또는 코드 검색..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  updateParams({ search: searchInput });
                }
              }}
              className="w-full px-3 py-2 border border-slate-200 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-whale-500"
            />
          </div>

          {/* Market filter */}
          <select
            value={market}
            onChange={(e) => updateParams({ market: e.target.value })}
            className="px-3 py-2 border border-slate-200 rounded-md text-sm bg-white"
          >
            <option value="">전체 시장</option>
            <option value="KOSPI">KOSPI</option>
            <option value="KOSDAQ">KOSDAQ</option>
          </select>

          <button
            onClick={() => updateParams({ search: searchInput })}
            className="px-4 py-2 bg-whale-600 text-white rounded-md text-sm hover:bg-whale-700"
          >
            검색
          </button>

          {(search || market) && (
            <button
              onClick={() => {
                setSearchInput("");
                updateParams({ search: "", market: "" });
              }}
              className="px-3 py-2 text-slate-500 hover:text-slate-700 text-sm"
            >
              초기화
            </button>
          )}
        </div>
      </div>

      {/* Results */}
      <div className="bg-white rounded-lg shadow-sm border border-slate-200">
        <div className="p-4 border-b border-slate-100">
          <span className="text-sm text-slate-500">총 {total.toLocaleString()}개 종목</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 text-slate-600">
                <th className="text-left px-4 py-3">종목코드</th>
                <th className="text-left px-4 py-3">종목명</th>
                <th className="text-center px-4 py-3">시장</th>
                <th className="text-center px-4 py-3">상태</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                Array.from({ length: 10 }).map((_, i) => (
                  <tr key={i} className="border-b border-slate-50">
                    <td colSpan={4} className="px-4 py-3">
                      <div className="h-4 bg-slate-100 rounded animate-pulse" />
                    </td>
                  </tr>
                ))
              ) : stocks.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-slate-400">
                    검색 결과가 없습니다
                  </td>
                </tr>
              ) : (
                stocks.map((stock: any) => (
                  <tr key={stock.ticker} className="border-b border-slate-50 hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3">
                      <Link href={`/stocks/${stock.ticker}`} className="text-whale-600 hover:text-whale-700 font-mono">
                        {stock.ticker}
                      </Link>
                    </td>
                    <td className="px-4 py-3 font-medium">
                      <Link href={`/stocks/${stock.ticker}`} className="hover:text-whale-600">
                        {stock.name}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`inline-block px-2 py-0.5 rounded text-xs ${
                        stock.market === "KOSPI" ? "bg-blue-50 text-blue-600" : "bg-purple-50 text-purple-600"
                      }`}>
                        {stock.market}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`w-2 h-2 inline-block rounded-full ${stock.is_active ? "bg-green-400" : "bg-slate-300"}`} />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2 p-4 border-t border-slate-100">
            <button
              disabled={page <= 1}
              onClick={() => updateParams({ page: String(page - 1) })}
              className="px-3 py-1 rounded text-sm border border-slate-200 disabled:opacity-50 hover:bg-slate-50"
            >
              이전
            </button>
            <span className="text-sm text-slate-500">
              {page} / {totalPages}
            </span>
            <button
              disabled={page >= totalPages}
              onClick={() => updateParams({ page: String(page + 1) })}
              className="px-3 py-1 rounded text-sm border border-slate-200 disabled:opacity-50 hover:bg-slate-50"
            >
              다음
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
