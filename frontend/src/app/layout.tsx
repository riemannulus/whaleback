import type { Metadata } from "next";
import { QueryProvider } from "@/providers/query-provider";
import { NavBar } from "@/components/layout/nav-bar";
import "./globals.css";

export const metadata: Metadata = {
  title: "Whaleback - 한국 주식 분석",
  description: "KOSPI/KOSDAQ 퀀트 분석, 수급 추적, 섹터 트렌드",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body className="min-h-screen bg-slate-50">
        <QueryProvider>
          <NavBar />
          <main className="container mx-auto px-4 py-6 max-w-7xl">
            {children}
          </main>
        </QueryProvider>
      </body>
    </html>
  );
}
