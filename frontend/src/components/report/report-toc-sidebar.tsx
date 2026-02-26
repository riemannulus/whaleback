"use client";

import type { ParsedReportSection } from "@/types/api";

interface ReportTOCSidebarProps {
  sections: ParsedReportSection[];
  activeId: string;
  onScrollTo: (id: string) => void;
}

export default function ReportTOCSidebar({
  sections,
  activeId,
  onScrollTo,
}: ReportTOCSidebarProps) {
  return (
    <nav className="no-print hidden w-60 shrink-0 lg:block">
      <div className="sticky top-24 max-h-[calc(100vh-6rem)] overflow-y-auto pr-4 border-r border-slate-200">
        <p className="mb-4 text-xs font-semibold uppercase tracking-widest text-slate-400">
          목차
        </p>
        <ul className="space-y-0.5">
          {sections.map((section, index) => {
            const isActive = section.id === activeId;
            return (
              <li key={section.id}>
                <button
                  onClick={() => onScrollTo(section.id)}
                  className={`w-full rounded-md px-3 py-2 text-left text-sm transition-all duration-200 border-l-2 ${
                    isActive
                      ? "border-violet-500 bg-violet-50 font-medium text-violet-700"
                      : "border-transparent text-slate-500 hover:bg-slate-50 hover:text-slate-800"
                  }`}
                >
                  <span className="mr-2 text-slate-300">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  {section.title}
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </nav>
  );
}
