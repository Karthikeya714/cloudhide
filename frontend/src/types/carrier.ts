export interface CarrierMetrics {
  id: string;
  original_filename: string;
  width: number;
  height: number;
  pixel_count: number;
  raw_capacity_bytes: number;
  max_payload_bytes: number;
  shannon_entropy: number;
  edge_density: number;
  distortion_risk: number;
  capacity_score: number;
  entropy_score: number;
  edge_score: number;
  distortion_score: number;
  overall_score: number;
  explanation: string[];
  created_at: string;
}

export interface CarrierRankResponse {
  carriers: CarrierMetrics[];
  recommended: CarrierMetrics[];
}
