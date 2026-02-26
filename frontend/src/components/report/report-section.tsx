interface ReportSectionProps {
  id: string;
  sectionNumber: number;
  title: string;
  subtitle?: string;
  accentColor?: string;
  children: React.ReactNode;
}

export default function ReportSection({
  id,
  sectionNumber,
  title,
  subtitle,
  accentColor = "border-slate-300",
  children,
}: ReportSectionProps) {
  return (
    <section
      id={id}
      data-section-id={id}
      className={`scroll-mt-24 mb-12 border-l-4 pl-4 ${accentColor}`}
    >
      <div className="flex items-baseline gap-3 pb-3 border-b border-slate-200">
        <span className="text-sm font-mono tabular-nums text-slate-300">
          {String(sectionNumber).padStart(2, "0")}
        </span>
        <h2 className="text-xl font-bold tracking-tight text-slate-900">
          {title}
        </h2>
        {subtitle && (
          <span className="text-sm text-slate-400">{subtitle}</span>
        )}
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}
