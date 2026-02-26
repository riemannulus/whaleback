"use client";

import { useRef, useEffect } from "react";
import type { ParsedReportSection } from "@/types/api";

interface ReportTOCMobileProps {
  sections: ParsedReportSection[];
  activeId: string;
  onScrollTo: (id: string) => void;
}

export default function ReportTOCMobile({
  sections,
  activeId,
  onScrollTo,
}: ReportTOCMobileProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const activeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    activeRef.current?.scrollIntoView({
      inline: "center",
      behavior: "smooth",
      block: "nearest",
    });
  }, [activeId]);

  if (sections.length === 0) return null;

  return (
    <div className="no-print sticky top-16 z-20 -mx-4 mb-6 border-b border-slate-200 bg-slate-50/95 px-4 py-2 backdrop-blur-sm lg:hidden">
      <div
        ref={scrollRef}
        className="flex gap-2 overflow-x-auto py-1 scrollbar-hide"
      >
        {sections.map((section) => {
          const isActive = section.id === activeId;
          return (
            <button
              key={section.id}
              ref={isActive ? activeRef : undefined}
              onClick={() => onScrollTo(section.id)}
              className={`shrink-0 rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                isActive
                  ? "border border-violet-300 bg-violet-100 text-violet-700"
                  : "border border-slate-200 bg-white text-slate-500"
              }`}
            >
              {section.title}
            </button>
          );
        })}
      </div>
    </div>
  );
}
