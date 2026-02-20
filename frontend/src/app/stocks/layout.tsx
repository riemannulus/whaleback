import { Suspense } from "react";

export default function StocksLayout({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<div className="p-8 text-center text-slate-400">로딩 중...</div>}>{children}</Suspense>;
}
