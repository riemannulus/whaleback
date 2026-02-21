"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/", label: "대시보드" },
  { href: "/stocks", label: "종목" },
  { href: "/analysis/quant", label: "퀀트분석" },
  { href: "/analysis/whale", label: "수급분석" },
  { href: "/analysis/trend", label: "추세분석" },
  { href: "/analysis/sector-flow", label: "섹터수급" },
];

export function NavBar() {
  const pathname = usePathname();

  return (
    <nav className="bg-white border-b border-slate-200 shadow-sm">
      <div className="container mx-auto px-4 max-w-7xl">
        <div className="flex items-center justify-between h-16">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-2xl">🐋</span>
            <span className="text-xl font-bold text-whale-700">Whaleback</span>
          </Link>
          <div className="flex items-center gap-1 overflow-x-auto scrollbar-hide flex-nowrap">
            {navItems.map((item) => {
              const isActive =
                item.href === "/"
                  ? pathname === "/"
                  : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors whitespace-nowrap ${
                    isActive
                      ? "bg-whale-50 text-whale-700"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </nav>
  );
}
