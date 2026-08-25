import { useEffect, useState } from "react";
import Card from "../components/Card";
import { apiErrorMessage, downloadUrl, listTransfers, recoverTransfer } from "../services/api";
import type { TransferRecoverResponse, TransferSummary } from "../types/transfer";

export default function RecoverFile() {
  const [transfers, setTransfers] = useState<TransferSummary[]>([]);
  const [transferId, setTransferId] = useState("");
  const [isRecovering, setIsRecovering] = useState(false);
  const [result, setResult] = useState<TransferRecoverResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listTransfers()
      .then(setTransfers)
      .catch(() => {
        /* transfer picker is a convenience; the manual ID field still works */
      });
  }, []);

  const handleRecover = async () => {
    if (!transferId.trim()) return;
    setIsRecovering(true);
    setResult(null);
    setError(null);
    try {
      setResult(await recoverTransfer(transferId.trim()));
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setIsRecovering(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-100">Recover File</h1>
        <p className="mt-1 text-slate-400">
          Reconstruct and decrypt the original file from its stego images.
        </p>
      </div>

      <Card title="Transfer Lookup">
        <div className="space-y-4">
          <label className="block text-sm text-slate-400">
            Transfer ID
            <input
              type="text"
              value={transferId}
              onChange={(e) => setTransferId(e.target.value)}
              placeholder="e.g. e4048b84-c6e3-45b3-8eb7-5baf8fec5a3f"
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm text-slate-100 focus:border-indigo-500 focus:outline-none"
            />
          </label>

          {transfers.length > 0 && (
            <div>
              <p className="mb-1 text-xs text-slate-500">Or pick a recent transfer:</p>
              <div className="flex flex-wrap gap-2">
                {transfers.slice(0, 8).map((t) => (
                  <button
                    key={t.id}
                    onClick={() => setTransferId(t.id)}
                    className={`rounded-md border px-3 py-1.5 text-xs transition-colors ${
                      transferId === t.id
                        ? "border-indigo-500 bg-indigo-500/10 text-indigo-300"
                        : "border-slate-700 text-slate-300 hover:border-slate-600"
                    }`}
                  >
                    {t.original_filename} · {t.status}
                  </button>
                ))}
              </div>
            </div>
          )}

          <button
            onClick={handleRecover}
            disabled={!transferId.trim() || isRecovering}
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isRecovering ? "Recovering…" : "Recover"}
          </button>
        </div>
      </Card>

      {error && (
        <Card>
          <p className="text-sm text-rose-400">{error}</p>
        </Card>
      )}

      {result && (
        <Card title="Recovery Result">
          <div className="space-y-3 text-sm">
            <p className="text-slate-300">
              Status: <span className="font-medium text-emerald-400">{result.status}</span>
            </p>
            <p className="text-slate-300">
              Integrity verified:{" "}
              <span className="font-medium text-emerald-400">
                {result.integrity_verified ? "Yes — SHA-256 hash matches original" : "No"}
              </span>
            </p>
            <p className="text-slate-300">
              File: <span className="font-medium">{result.original_filename}</span> (
              {result.recovered_size.toLocaleString()} bytes)
            </p>
            <p className="text-slate-300">
              Recovery time:{" "}
              <span className="font-medium">{result.processing_time_ms.toFixed(0)} ms</span>
            </p>
            <a
              href={downloadUrl(result.transfer_id)}
              className="inline-block rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-emerald-500"
            >
              Download Recovered File
            </a>
          </div>
        </Card>
      )}
    </div>
  );
}
