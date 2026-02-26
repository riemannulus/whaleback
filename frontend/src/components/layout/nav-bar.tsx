"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import { Menu, X, Github, Linkedin, Mail } from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "대시보드" },
  { href: "/stocks", label: "종목" },
  { href: "/analysis/quant", label: "퀀트분석" },
  { href: "/analysis/whale", label: "수급분석" },
  { href: "/analysis/trend", label: "추세분석" },
  { href: "/analysis/sector-flow", label: "섹터수급" },
];

const creatorLinks = [
  {
    href: "https://github.com/riemannulus",
    icon: Github,
    label: "GitHub",
    displayName: "riemannulus",
    ariaLabel: "riemannulus GitHub profile",
  },
  {
    href: "https://linkedin.com/in/riemannulus",
    icon: Linkedin,
    label: "LinkedIn",
    displayName: "Suho Lee",
    ariaLabel: "riemannulus LinkedIn profile",
  },
  {
    href: "mailto:0xbadcaffee@gmail.com",
    icon: Mail,
    label: "Email",
    displayName: "0xbadcaffee",
    ariaLabel: "0xbadcaffee@gmail.com",
  },
];

export function NavBar() {
  const pathname = usePathname();
  const [drawerOpen, setDrawerOpen] = useState(false);

  const isNavActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  // Close drawer on route change
  useEffect(() => {
    setDrawerOpen(false);
  }, [pathname]);

  // Prevent body scroll when drawer is open
  useEffect(() => {
    if (!drawerOpen) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [drawerOpen]);

  // Close drawer on Escape key
  useEffect(() => {
    if (!drawerOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setDrawerOpen(false);
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [drawerOpen]);

  return (
    <>
      <nav className="bg-white border-b border-slate-200 shadow-sm">
        <div className="container mx-auto px-4 max-w-7xl">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link href="/" className="flex items-center gap-2 shrink-0">
              <span className="text-2xl">🐋</span>
              <span className="text-xl font-bold text-whale-700">Whaleback</span>
            </Link>

            {/* Desktop nav links */}
            <div className="hidden md:flex items-center gap-1 overflow-x-auto scrollbar-hide flex-nowrap">
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "px-3 py-2 rounded-md text-sm font-medium transition-colors whitespace-nowrap",
                    isNavActive(item.href)
                      ? "bg-whale-50 text-whale-700"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                  )}
                >
                  {item.label}
                </Link>
              ))}
            </div>

            {/* Desktop creator icons */}
            <div className="hidden md:flex items-center gap-2 ml-3 shrink-0">
              {creatorLinks.map(({ href, icon: Icon, ariaLabel }) => (
                <a
                  key={href}
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={ariaLabel}
                  className="text-slate-400 hover:text-slate-600 transition-colors"
                >
                  <Icon className="w-4 h-4" />
                </a>
              ))}
            </div>

            {/* Mobile hamburger button */}
            <button
              type="button"
              className="md:hidden p-2 rounded-md text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors"
              aria-label={drawerOpen ? "메뉴 닫기" : "메뉴 열기"}
              aria-expanded={drawerOpen}
              aria-controls="mobile-nav-drawer"
              onClick={() => setDrawerOpen((prev) => !prev)}
            >
              {drawerOpen ? (
                <X className="w-5 h-5" />
              ) : (
                <Menu className="w-5 h-5" />
              )}
            </button>
          </div>
        </div>
      </nav>

      {/* Mobile drawer overlay + panel */}
      {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
      <div
        aria-hidden={!drawerOpen}
        {...(!drawerOpen ? ({ inert: "" } as any) : {})}
        className={cn(
          "fixed inset-0 z-50 md:hidden",
          drawerOpen ? "pointer-events-auto" : "pointer-events-none"
        )}
      >
        {/* Backdrop */}
        <div
          role="button"
          tabIndex={0}
          className={cn(
            "absolute inset-0 bg-black/40 backdrop-blur-sm transition-opacity duration-300 ease-in-out",
            drawerOpen ? "opacity-100" : "opacity-0"
          )}
          onClick={() => setDrawerOpen(false)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") setDrawerOpen(false);
          }}
          aria-label="메뉴 닫기"
        />

        {/* Slide-in panel */}
        <div
          id="mobile-nav-drawer"
          role="dialog"
          aria-modal="true"
          aria-label="내비게이션 메뉴"
          className={cn(
            "absolute top-0 right-0 h-full w-4/5 max-w-[320px] bg-white shadow-2xl flex flex-col",
            "transition-transform duration-300 ease-in-out",
            drawerOpen ? "translate-x-0" : "translate-x-full"
          )}
        >
          {/* Drawer header */}
          <div className="flex items-center justify-between px-5 h-16 border-b border-slate-100 shrink-0">
            <span className="text-base font-semibold text-whale-700">
              메뉴
            </span>
            <button
              type="button"
              aria-label="메뉴 닫기"
              className="p-2 rounded-md text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors"
              onClick={() => setDrawerOpen(false)}
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Nav items */}
          <nav className="flex-1 overflow-y-auto py-3 px-3">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center px-4 py-3 rounded-lg text-base font-medium transition-colors mb-1",
                  isNavActive(item.href)
                    ? "bg-whale-50 text-whale-700"
                    : "text-slate-700 hover:text-slate-900 hover:bg-slate-50"
                )}
                onClick={() => setDrawerOpen(false)}
              >
                {item.label}
              </Link>
            ))}
          </nav>

          {/* Creator credits */}
          <div className="shrink-0 border-t border-slate-100 px-5 py-4">
            <p className="text-xs text-slate-400 mb-2">만든 사람</p>
            <div className="flex flex-col gap-2">
              {creatorLinks.map(({ href, icon: Icon, label, displayName, ariaLabel }) => (
                <a
                  key={href}
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={ariaLabel}
                  className="flex items-center gap-2 text-xs text-slate-400 hover:text-slate-600 transition-colors w-fit"
                >
                  <Icon className="w-3.5 h-3.5 shrink-0" />
                  <span>{displayName}</span>
                  <span className="text-slate-300">· {label}</span>
                </a>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
