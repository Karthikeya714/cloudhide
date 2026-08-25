import { useEffect, useState } from "react";
import BarChart from "../components/charts/BarChart";
import LineChart from "../components/charts/LineChart";
import Card from "../components/Card";
import StatTile from "../components/StatTile";
import StatusBadge from "../components/StatusBadge";
import { getAnalytics } from "../services/api";
import type { AnalyticsResponse } from "../types/analytics";

function formatMs(value: number | null): string {
  if (value === null) return "—";
  return `${value.toFixed(1)} ms`;
}

function formatPercent(value: number | null): string {
  if (value === null) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

function formatDb(value: number | null): string {
  if (value === null) return "—";
  return `${value.toFixed(1)} dB`;
}

export default function Analytics() {
  const [data, setData] = useState<AnalyticsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAnalytics()
      .then(setData)
      .catch(() => setError("Unable to load analytics from the CloudHide backend."));
  }, []);

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-semibold text-slate-100">Analytics</h1>
        <p className="text-sm text-rose-400">{error}</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-semibold text-slate-100">Analytics</h1>
        <p className="text-sm text-slate-400">Loading…</p>
      </div>
    );
  }

  const { summary, recent_transfers } = data;

  const timingData = [
    { label: "Encryption", value: summary.avg_encryption_time_ms },
    { label: "Fragmentation", value: summary.avg_fragmentation_time_ms },
    { label: "Embedding", value: summary.avg_embedding_time_ms },
    { label: "Extraction", value: summary.avg_extraction_time_ms },
    { label: "Recovery", value: summary.avg_recovery_time_ms },
  ].filter((d): d is { label: string; value: number } => d.value !== null);

  const processingTimeSeries = [...recent_transfers]
    .reverse()
    .filter((t) => t.processing_time_ms !== null)
    .map((t, i) => ({ label: `#${i + 1}`, value: t.processing_time_ms as number }));

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-slate-100">Analytics</h1>
        <p className="mt-1 text-slate-400">
          Measurable results computed from real transfers stored in the database.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="Files Hidden" value={summary.files_hidden.toString()} />
        <StatTile label="Successful Recoveries" value={summary.successful_recoveries.toString()} />
        <StatTile label="Recovery Rate" value={formatPercent(summary.recovery_rate)} />
        <StatTile label="Average Processing Time" value={formatMs(summary.avg_processing_time_ms)} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="Processing Time Breakdown" className="lg:col-span-1">
          <BarChart data={timingData} unit=" ms" />
        </Card>

        <Card title="Total Hide Time per Transfer (recent)" className="lg:col-span-1">
          <LineChart data={processingTimeSeries} unit=" ms" />
        </Card>
      </div>

      <Card title="Security & Quality Metrics">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile
            label="Average PSNR"
            value={formatDb(summary.avg_psnr_db)}
            hint="Higher is less visually distorted"
          />
          <StatTile
            label="Average SSIM"
            value={summary.avg_ssim !== null ? summary.avg_ssim.toFixed(3) : "—"}
            hint="1.0 = structurally identical"
          />
          <StatTile
            label="Carrier Capacity Utilization"
            value={
              summary.avg_capacity_utilization_percent !== null
                ? `${summary.avg_capacity_utilization_percent.toFixed(1)}%`
                : "—"
            }
          />
          <StatTile
            label="Failed Operations"
            value={(summary.failed_hides + summary.failed_recoveries).toString()}
            hint={`${summary.failed_hides} hide, ${summary.failed_recoveries} recovery`}
          />
        </div>
      </Card>

      <Card title="Recent Transfers">
        {recent_transfers.length === 0 ? (
          <p className="text-sm text-slate-400">No transfers yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-slate-500">
                  <th className="py-2 pr-4 font-medium">File</th>
                  <th className="py-2 pr-4 font-medium">Status</th>
                  <th className="py-2 pr-4 font-medium">Fragments</th>
                  <th className="py-2 pr-4 font-medium">Hide Time</th>
                  <th className="py-2 pr-4 font-medium">Recovery Time</th>
                  <th className="py-2 pr-4 font-medium">PSNR</th>
                  <th className="py-2 pr-4 font-medium">Created</th>
                </tr>
              </thead>
              <tbody>
                {recent_transfers.map((t) => (
                  <tr key={t.id} className="border-b border-slate-800/60 last:border-0">
                    <td className="py-2 pr-4 text-slate-200">{t.original_filename}</td>
                    <td className="py-2 pr-4">
                      <StatusBadge status={t.status} />
                    </td>
                    <td className="py-2 pr-4 text-slate-400">{t.fragment_count}</td>
                    <td className="py-2 pr-4 text-slate-400">{formatMs(t.processing_time_ms)}</td>
                    <td className="py-2 pr-4 text-slate-400">{formatMs(t.recovery_time_ms)}</td>
                    <td className="py-2 pr-4 text-slate-400">{formatDb(t.avg_psnr_db)}</td>
                    <td className="py-2 pr-4 text-slate-500">
                      {new Date(t.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
