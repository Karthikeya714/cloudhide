export interface AnalyticsSummary {
  total_transfers: number;
  files_hidden: number;
  successful_recoveries: number;
  failed_hides: number;
  failed_recoveries: number;
  recovery_rate: number | null;

  avg_encryption_time_ms: number | null;
  avg_fragmentation_time_ms: number | null;
  avg_embedding_time_ms: number | null;
  avg_extraction_time_ms: number | null;
  avg_recovery_time_ms: number | null;
  avg_processing_time_ms: number | null;

  avg_psnr_db: number | null;
  avg_ssim: number | null;
  avg_capacity_utilization_percent: number | null;
}

export interface RecentTransfer {
  id: string;
  original_filename: string;
  status: string;
  fragment_count: number;
  processing_time_ms: number | null;
  recovery_time_ms: number | null;
  avg_psnr_db: number | null;
  avg_ssim: number | null;
  created_at: string;
}

export interface AnalyticsResponse {
  summary: AnalyticsSummary;
  recent_transfers: RecentTransfer[];
}
