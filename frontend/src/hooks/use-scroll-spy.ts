"use client";

import { useEffect, useState, useRef } from "react";

export function useScrollSpy(sectionIds: string[]): string {
  const [activeId, setActiveId] = useState<string>("");
  const observerRef = useRef<IntersectionObserver | null>(null);

  useEffect(() => {
    if (sectionIds.length === 0) return;

    const visibleSections = new Map<string, IntersectionObserverEntry>();

    observerRef.current = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          const id = entry.target.getAttribute("data-section-id");
          if (!id) continue;
          if (entry.isIntersecting) {
            visibleSections.set(id, entry);
          } else {
            visibleSections.delete(id);
          }
        }

        if (visibleSections.size > 0) {
          let topMost: string | null = null;
          let topMostY = Infinity;
          visibleSections.forEach((entry, id) => {
            const y = entry.boundingClientRect.top;
            if (y < topMostY) {
              topMostY = y;
              topMost = id;
            }
          });
          if (topMost) setActiveId(topMost);
        }
      },
      {
        rootMargin: "-80px 0px -60% 0px",
        threshold: [0, 0.25],
      }
    );

    const timer = setTimeout(() => {
      for (const id of sectionIds) {
        const el = document.querySelector(`[data-section-id="${id}"]`);
        if (el) observerRef.current?.observe(el);
      }
    }, 100);

    return () => {
      clearTimeout(timer);
      observerRef.current?.disconnect();
    };
  }, [sectionIds]);

  return activeId;
}
