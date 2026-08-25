import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Card from "../components/Card";
import StatTile from "../components/StatTile";
import StatusBadge from "../components/StatusBadge";
import { apiErrorMessage, getAnalytics } from "../services/api";
import type { AnalyticsResponse } from "../types/analytics";

function formatMs(value: number | null): string {
  if (value === null) return "—";
  return value < 1000 ? `${value.toFixed(0)} ms` : `${(value / 1000).toFixed(2)} s`;
}

function formatPercent(value: number | null): string {
  if (value === null) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

export default function Dashboard() {
  const [data, setData] = useState<AnalyticsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAnalytics(5)
      .then(setData)
      .catch((err) => setError(apiErrorMessage(err)));
  }, []);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-slate-100">Dashboard</h1>
        <p className="mt-1 text-slate-400">
          Overview of encrypted transfers hidden inside carrier images.
        </p>
      </div>

      {error && (
        <Card>
          <p className="text-sm text-rose-400">{error}</p>
        </Card>
      )}

      {!error && !data && <p className="text-sm text-slate-400">Loading…</p>}

      {data && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <StatTile label="Files Hidden" value={data.summary.files_hidden.toString()} />
            <StatTile
              label="Successful Recoveries"
              value={data.summary.successful_recoveries.toString()}
            />
            <StatTile label="Recovery Rate" value={formatPercent(data.summary.recovery_rate)} />
            <StatTile
              label="Average PSNR"
              value={
                data.summary.avg_psnr_db !== null
                  ? `${data.summary.avg_psnr_db.toFixed(1)} dB`
                  : "—"
              }
            />
            <StatTile
              label="Average Processing Time"
              value={formatMs(data.summary.avg_processing_time_ms)}
            />
            <StatTile label="Total Transfers" value={data.summary.total_transfers.toString()} />
          </div>

          <Card
            title="Recent Transfers"
            action={
              <Link to="/analytics" className="text-xs font-medium text-indigo-400 hover:underline">
                View analytics
              </Link>
            }
          >
            {data.recent_transfers.length === 0 ? (
              <p className="text-sm text-slate-400">
                No transfers yet. Head to Hide File to get started.
              </p>
            ) : (
              <ul className="divide-y divide-slate-800">
                {data.recent_transfers.map((t) => (
                  <li key={t.id} className="flex items-center justify-between py-3">
                    <div>
                      <Link
                        to={`/transfers/${t.id}`}
                        className="text-sm font-medium text-slate-200 hover:text-indigo-300"
                      >
                        {t.original_filename}
                      </Link>
                      <p className="text-xs text-slate-500">
                        {new Date(t.created_at).toLocaleString()}
                      </p>
                    </div>
                    <StatusBadge status={t.status} />
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
