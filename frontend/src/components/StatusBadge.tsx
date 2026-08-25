const STATUS_STYLES: Record<string, string> = {
  completed: "text-indigo-300 bg-indigo-500/10",
  recovered: "text-emerald-300 bg-emerald-500/10",
  failed: "text-rose-300 bg-rose-500/10",
  recovery_failed: "text-rose-300 bg-rose-500/10",
  fragmented: "text-amber-300 bg-amber-500/10",
  pending: "text-slate-300 bg-slate-500/10",
};

export default function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`rounded px-2 py-0.5 text-xs font-medium ${
        STATUS_STYLES[status] ?? "text-slate-300 bg-slate-500/10"
      }`}
    >
      {status}
    </span>
  );
}
