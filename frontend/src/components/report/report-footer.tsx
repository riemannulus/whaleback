interface ReportFooterProps {
  modelUsed: string;
  condenserModelUsed: string;
  computedAt: string;
  tradeDate: string;
}

export default function ReportFooter({
  modelUsed,
  condenserModelUsed,
  computedAt,
  tradeDate,
}: ReportFooterProps) {
  const formatDateTime = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleString("ko-KR", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return iso;
    }
  };

  return (
    <footer className="mt-16 border-t border-slate-200 pt-6">
      <p className="text-xs text-slate-400">
        분석 모델: {modelUsed} · 요약 모델: {condenserModelUsed}
      </p>
      <p className="mt-1 text-xs text-slate-400">
        생성일시: {formatDateTime(computedAt)} · 기준일: {tradeDate}
      </p>
      <p className="mt-4 max-w-xl text-xs leading-relaxed text-slate-300">
        본 리포트는 AI가 자동 생성한 참고 자료이며, 투자 판단의 근거로 사용하기에
        적합하지 않습니다. 모든 투자 결정은 본인의 판단과 책임 하에 이루어져야
        합니다.
      </p>
    </footer>
  );
}
