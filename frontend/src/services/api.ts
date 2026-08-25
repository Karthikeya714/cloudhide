import axios from "axios";
import type { AnalyticsResponse } from "../types/analytics";
import type { CarrierMetrics, CarrierRankResponse } from "../types/carrier";
import type {
  TransferDetail,
  TransferHideResponse,
  TransferRecoverResponse,
  TransferSummary,
} from "../types/transfer";

export const api = axios.create({
  baseURL: "/",
  timeout: 60_000,
});

export interface HealthStatus {
  status: string;
  app_name: string;
  environment: string;
  version: string;
}

export async function getHealth(): Promise<HealthStatus> {
  const { data } = await api.get<HealthStatus>("/health");
  return data;
}

export async function getAnalytics(recentLimit = 20): Promise<AnalyticsResponse> {
  const { data } = await api.get<AnalyticsResponse>("/api/analytics", {
    params: { recent_limit: recentLimit },
  });
  return data;
}

export async function uploadCarrier(
  file: File,
  onProgress?: (percent: number) => void,
): Promise<CarrierMetrics> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post<CarrierMetrics>("/api/carriers/upload", form, {
    onUploadProgress: (event) => {
      if (onProgress && event.total) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    },
  });
  return data;
}

export async function rankCarriers(limit = 10): Promise<CarrierRankResponse> {
  const { data } = await api.get<CarrierRankResponse>("/api/carriers/rank", {
    params: { limit },
  });
  return data;
}

export async function hideFile(
  file: File,
  fragmentCount: number,
  onProgress?: (percent: number) => void,
): Promise<TransferHideResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("fragment_count", String(fragmentCount));
  const { data } = await api.post<TransferHideResponse>("/api/transfers/hide", form, {
    onUploadProgress: (event) => {
      if (onProgress && event.total) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    },
  });
  return data;
}

export async function listTransfers(): Promise<TransferSummary[]> {
  const { data } = await api.get<TransferSummary[]>("/api/transfers");
  return data;
}

export async function getTransfer(transferId: string): Promise<TransferDetail> {
  const { data } = await api.get<TransferDetail>(`/api/transfers/${transferId}`);
  return data;
}

export async function recoverTransfer(transferId: string): Promise<TransferRecoverResponse> {
  const { data } = await api.post<TransferRecoverResponse>(
    `/api/transfers/${transferId}/recover`,
  );
  return data;
}

export function downloadUrl(transferId: string): string {
  return `/api/transfers/${transferId}/download`;
}

export function apiErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (err.message) return err.message;
  }
  if (err instanceof Error) return err.message;
  return "Something went wrong.";
}
