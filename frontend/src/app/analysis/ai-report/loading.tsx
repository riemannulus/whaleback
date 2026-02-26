export default function AIReportLoading() {
  return (
    <div className="animate-pulse">
      <div className="mb-8 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-8 w-32 rounded bg-slate-200" />
          <div className="h-6 w-48 rounded bg-slate-100" />
        </div>
        <div className="h-8 w-24 rounded bg-slate-100" />
      </div>
      <div className="flex gap-8">
        <div className="hidden w-60 shrink-0 lg:block">
          {[...Array(12)].map((_, i) => (
            <div
              key={i}
              className="mb-3 h-4 rounded bg-slate-100"
              style={{ width: `${70 + (i * 7) % 30}%` }}
            />
          ))}
        </div>
        <div className="flex-1">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="mb-12">
              <div className="mb-4 h-6 w-48 rounded bg-slate-200" />
              <div className="space-y-2">
                {[...Array(5)].map((_, j) => (
                  <div
                    key={j}
                    className="h-4 rounded bg-slate-100"
                    style={{ width: `${60 + ((i * 5 + j * 8) % 40)}%` }}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
