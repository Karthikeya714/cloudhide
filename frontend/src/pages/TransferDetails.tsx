import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import Card from "../components/Card";
import StatTile from "../components/StatTile";
import StatusBadge from "../components/StatusBadge";
import { apiErrorMessage, downloadUrl, getTransfer, recoverTransfer } from "../services/api";
import type { TransferDetail } from "../types/transfer";

function formatMs(value: number | null): string {
  if (value === null) return "—";
  return `${value.toFixed(1)} ms`;
}

export default function TransferDetails() {
  const { transferId } = useParams<{ transferId: string }>();
  const [transfer, setTransfer] = useState<TransferDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isRecovering, setIsRecovering] = useState(false);
  const [recoverError, setRecoverError] = useState<string | null>(null);

  const load = () => {
    if (!transferId) return;
    getTransfer(transferId)
      .then(setTransfer)
      .catch((err) => setError(apiErrorMessage(err)));
  };

  useEffect(load, [transferId]);

  const handleRecover = async () => {
    if (!transferId) return;
    setIsRecovering(true);
    setRecoverError(null);
    try {
      await recoverTransfer(transferId);
      load();
    } catch (err) {
      setRecoverError(apiErrorMessage(err));
    } finally {
      setIsRecovering(false);
    }
  };

  if (error) {
    return (
      <div className="space-y-4">
        <Link to="/" className="text-sm text-indigo-400 hover:underline">
          &larr; Back
        </Link>
        <Card>
          <p className="text-sm text-rose-400">{error}</p>
        </Card>
      </div>
    );
  }

  if (!transfer) {
    return <p className="text-sm text-slate-400">Loading…</p>;
  }

  return (
    <div className="space-y-6">
      <div>
        <Link to="/" className="text-sm text-indigo-400 hover:underline">
          &larr; Back to dashboard
        </Link>
        <div className="mt-2 flex items-center gap-3">
          <h1 className="text-2xl font-semibold text-slate-100">{transfer.original_filename}</h1>
          <StatusBadge status={transfer.status} />
        </div>
        <p className="mt-1 font-mono text-xs text-slate-500">{transfer.id}</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="Fragments" value={transfer.fragment_count.toString()} />
        <StatTile label="Hide Time" value={formatMs(transfer.processing_time_ms)} />
        <StatTile label="Recovery Time" value={formatMs(transfer.recovery_time_ms)} />
        <StatTile label="Recovered" value={transfer.recovered ? "Yes" : "No"} />
      </div>

      <Card title="Pipeline Timing">
        <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-5">
          <div>
            <dt className="text-slate-500">Encryption</dt>
            <dd className="font-medium text-slate-200">{formatMs(transfer.encryption_time_ms)}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Fragmentation</dt>
            <dd className="font-medium text-slate-200">
              {formatMs(transfer.fragmentation_time_ms)}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">Embedding</dt>
            <dd className="font-medium text-slate-200">{formatMs(transfer.embedding_time_ms)}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Extraction</dt>
            <dd className="font-medium text-slate-200">{formatMs(transfer.extraction_time_ms)}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Recovery</dt>
            <dd className="font-medium text-slate-200">{formatMs(transfer.recovery_time_ms)}</dd>
          </div>
        </dl>
      </Card>

      <Card title="Stego Images">
        {transfer.stego_images.length === 0 ? (
          <p className="text-sm text-slate-400">No stego images.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-slate-500">
                  <th className="py-2 pr-4 font-medium">Fragment</th>
                  <th className="py-2 pr-4 font-medium">Carrier</th>
                  <th className="py-2 pr-4 font-medium">PSNR</th>
                  <th className="py-2 pr-4 font-medium">SSIM</th>
                  <th className="py-2 pr-4 font-medium">Capacity Used</th>
                </tr>
              </thead>
              <tbody>
                {transfer.stego_images
                  .slice()
                  .sort((a, b) => a.fragment_index - b.fragment_index)
                  .map((s) => (
                    <tr key={s.id} className="border-b border-slate-800/60 last:border-0">
                      <td className="py-2 pr-4 text-slate-300">#{s.fragment_index}</td>
                      <td className="py-2 pr-4 text-slate-300">{s.carrier_filename}</td>
                      <td className="py-2 pr-4 text-slate-400">
                        {s.psnr_db !== null ? `${s.psnr_db.toFixed(1)} dB` : "—"}
                      </td>
                      <td className="py-2 pr-4 text-slate-400">
                        {s.ssim !== null ? s.ssim.toFixed(3) : "—"}
                      </td>
                      <td className="py-2 pr-4 text-slate-400">
                        {s.capacity_utilization !== null
                          ? `${(s.capacity_utilization * 100).toFixed(1)}%`
                          : "—"}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card title="Recovery">
        {recoverError && <p className="mb-3 text-sm text-rose-400">{recoverError}</p>}
        <div className="flex items-center gap-3">
          <button
            onClick={handleRecover}
            disabled={isRecovering}
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isRecovering ? "Recovering…" : transfer.recovered ? "Recover Again" : "Recover"}
          </button>
          {transfer.recovered && (
            <a
              href={downloadUrl(transfer.id)}
              className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-emerald-500"
            >
              Download Recovered File
            </a>
          )}
        </div>
      </Card>
    </div>
  );
}
