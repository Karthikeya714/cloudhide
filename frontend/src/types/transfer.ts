export interface StegoImageSummary {
  id: string;
  fragment_id: string;
  carrier_id: string;
  storage_provider: string;
  storage_path: string;
}

export interface TransferHideResponse {
  transfer_id: string;
  fragment_count: number;
  selected_carrier_ids: string[];
  stego_images: StegoImageSummary[];
  processing_time_ms: number;
  status: string;
}

export interface TransferSummary {
  id: string;
  original_filename: string;
  fragment_count: number;
  status: string;
  processing_time_ms: number | null;
  created_at: string;
}

export interface FragmentSummary {
  id: string;
  fragment_index: number;
  size: number;
  sha256: string;
}

export interface StegoImageDetail {
  id: string;
  fragment_id: string;
  fragment_index: number;
  carrier_id: string;
  carrier_filename: string;
  psnr_db: number | null;
  ssim: number | null;
  capacity_utilization: number | null;
}

export interface TransferDetail extends TransferSummary {
  encrypted_file_id: string | null;
  encryption_time_ms: number | null;
  fragmentation_time_ms: number | null;
  embedding_time_ms: number | null;
  extraction_time_ms: number | null;
  recovery_time_ms: number | null;
  recovered: boolean;
  fragments: FragmentSummary[];
  stego_images: StegoImageDetail[];
}

export interface TransferRecoverResponse {
  transfer_id: string;
  status: string;
  original_filename: string;
  recovered_size: number;
  integrity_verified: boolean;
  processing_time_ms: number;
}
