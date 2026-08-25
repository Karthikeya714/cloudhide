import { useState } from "react";
import { Link } from "react-router-dom";
import Card from "../components/Card";
import Dropzone from "../components/Dropzone";
import ProgressBar from "../components/ProgressBar";
import { apiErrorMessage, hideFile, rankCarriers, uploadCarrier } from "../services/api";
import type { CarrierRankResponse } from "../types/carrier";
import type { TransferHideResponse } from "../types/transfer";

interface CarrierUpload {
  key: string;
  filename: string;
  progress: number;
  status: "uploading" | "done" | "error";
  score?: number;
  error?: string;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export default function HideFile() {
  const [secretFile, setSecretFile] = useState<File | null>(null);
  const [fragmentCount, setFragmentCount] = useState(3);

  const [carrierUploads, setCarrierUploads] = useState<CarrierUpload[]>([]);
  const [ranking, setRanking] = useState<CarrierRankResponse | null>(null);

  const [isHiding, setIsHiding] = useState(false);
  const [hideProgress, setHideProgress] = useState(0);
  const [hideResult, setHideResult] = useState<TransferHideResponse | null>(null);
  const [hideError, setHideError] = useState<string | null>(null);

  const refreshRanking = async () => {
    try {
      setRanking(await rankCarriers(10));
    } catch {
      // Ranking is a convenience view; ignore transient failures here.
    }
  };

  const handleCarrierFiles = (files: File[]) => {
    for (const file of files) {
      const key = `${file.name}-${file.size}-${Date.now()}-${Math.random()}`;
      setCarrierUploads((prev) => [
        ...prev,
        { key, filename: file.name, progress: 0, status: "uploading" },
      ]);

      uploadCarrier(file, (percent) => {
        setCarrierUploads((prev) =>
          prev.map((u) => (u.key === key ? { ...u, progress: percent } : u)),
        );
      })
        .then((metrics) => {
          setCarrierUploads((prev) =>
            prev.map((u) =>
              u.key === key ? { ...u, status: "done", score: metrics.overall_score } : u,
            ),
          );
          refreshRanking();
        })
        .catch((err) => {
          setCarrierUploads((prev) =>
            prev.map((u) =>
              u.key === key ? { ...u, status: "error", error: apiErrorMessage(err) } : u,
            ),
          );
        });
    }
  };

  const carriersReady = carrierUploads.filter((u) => u.status === "done").length;

  const handleHide = async () => {
    if (!secretFile) return;
    setIsHiding(true);
    setHideProgress(0);
    setHideResult(null);
    setHideError(null);
    try {
      const result = await hideFile(secretFile, fragmentCount, setHideProgress);
      setHideResult(result);
    } catch (err) {
      setHideError(apiErrorMessage(err));
    } finally {
      setIsHiding(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-100">Hide File</h1>
        <p className="mt-1 text-slate-400">
          Encrypt a secret file and hide it inside the best available carrier images.
        </p>
      </div>

      <Card title="1. Secret File">
        {secretFile ? (
          <div className="flex items-center justify-between rounded-md border border-slate-800 bg-slate-950/50 px-4 py-3">
            <div>
              <p className="text-sm font-medium text-slate-200">{secretFile.name}</p>
              <p className="text-xs text-slate-500">{formatBytes(secretFile.size)}</p>
            </div>
            <button
              onClick={() => setSecretFile(null)}
              className="text-xs font-medium text-slate-400 hover:text-slate-200"
            >
              Remove
            </button>
          </div>
        ) : (
          <Dropzone
            label="Drop your secret file here"
            hint="Any file type — it will be encrypted with AES-256-GCM before hiding"
            onFiles={(files) => setSecretFile(files[0])}
          />
        )}
      </Card>

      <Card title="2. Carrier Images">
        <Dropzone
          label="Drop PNG carrier images here"
          hint="Upload several images — CloudHide will analyze and rank them automatically"
          accept="image/png"
          multiple
          onFiles={handleCarrierFiles}
        />

        {carrierUploads.length > 0 && (
          <ul className="mt-4 space-y-2">
            {carrierUploads.map((u) => (
              <li key={u.key} className="rounded-md border border-slate-800 px-3 py-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-200">{u.filename}</span>
                  {u.status === "done" && (
                    <span className="text-xs text-emerald-400">
                      score {u.score?.toFixed(1)}/100
                    </span>
                  )}
                  {u.status === "error" && (
                    <span className="text-xs text-rose-400">{u.error}</span>
                  )}
                </div>
                {u.status === "uploading" && (
                  <div className="mt-2">
                    <ProgressBar percent={u.progress} />
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}

        {ranking && ranking.recommended.length > 0 && (
          <div className="mt-4 rounded-md border border-indigo-500/30 bg-indigo-500/5 p-3">
            <p className="text-xs font-medium text-indigo-300">Recommended carriers</p>
            <ol className="mt-1 space-y-1 text-xs text-slate-400">
              {ranking.recommended.map((c, i) => (
                <li key={c.id}>
                  {i + 1}. {c.original_filename} — score {c.overall_score.toFixed(1)}/100,{" "}
                  {c.max_payload_bytes.toLocaleString()} bytes capacity
                </li>
              ))}
            </ol>
          </div>
        )}
      </Card>

      <Card title="3. Fragmentation Settings">
        <label className="block text-sm text-slate-400">
          Number of fragments
          <input
            type="number"
            min={1}
            max={64}
            value={fragmentCount}
            onChange={(e) => setFragmentCount(Number(e.target.value))}
            className="mt-1 w-32 rounded-md border border-slate-700 bg-slate-950 px-3 py-1.5 text-slate-100 focus:border-indigo-500 focus:outline-none"
          />
        </label>
        <p className="mt-2 text-xs text-slate-500">
          The secret file will be split into this many encrypted fragments, each hidden in a
          separate carrier image. You have {carriersReady} carrier{carriersReady === 1 ? "" : "s"}{" "}
          ready.
        </p>
      </Card>

      <div className="flex items-center gap-4">
        <button
          onClick={handleHide}
          disabled={!secretFile || isHiding}
          className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isHiding ? "Hiding…" : "Hide File"}
        </button>
        {isHiding && (
          <div className="w-48">
            <ProgressBar percent={hideProgress} />
          </div>
        )}
      </div>

      {hideError && (
        <Card>
          <p className="text-sm text-rose-400">{hideError}</p>
        </Card>
      )}

      {hideResult && (
        <Card title="Transfer Complete">
          <div className="space-y-2 text-sm">
            <p className="text-slate-300">
              Status: <span className="font-medium text-emerald-400">{hideResult.status}</span>
            </p>
            <p className="text-slate-300">
              Fragments: <span className="font-medium">{hideResult.fragment_count}</span>
            </p>
            <p className="text-slate-300">
              Processing time:{" "}
              <span className="font-medium">{hideResult.processing_time_ms.toFixed(0)} ms</span>
            </p>
            <p className="text-slate-300">
              Transfer ID:{" "}
              <Link
                to={`/transfers/${hideResult.transfer_id}`}
                className="font-mono text-indigo-400 hover:underline"
              >
                {hideResult.transfer_id}
              </Link>
            </p>
          </div>
        </Card>
      )}
    </div>
  );
}
