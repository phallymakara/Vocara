/**
 * Vocara Frontend Models (Domain Entities and DTO Types).
 */

export interface ApiKeyItem {
  id: string;
  name: string;
  key_prefix: string;
  status: string;
  rate_limit_per_minute: number;
  char_quota_per_month: number;
  chars_used_this_month: number;
  last_used_at: string | null;
  created_at: string;
}

export interface ApiKeyCreated extends ApiKeyItem {
  api_key: string;
}

export interface VoiceItem {
  id: string;
  name: string;
  language: string;
  voice_type: "built_in" | "cloned" | "designed";
  visibility: "public" | "private";
  description: string;
  modifiers: Record<string, unknown>;
  owner_id?: string | null;
  created_at?: string;
}

export interface TtsRequestPayload {
  text: string;
  voice_id: string;
  language: string;
  speed: number;
  output_format: "mp3" | "wav" | "flac";
  async_only?: boolean;
}

export interface JobItem {
  id: string;
  job_type: string;
  status: "queued" | "processing" | "completed" | "failed";
  owner_id: string;
  voice_id?: string;
  char_count: number;
  language: string;
  output_format: string;
  audio_duration_seconds: number;
  error_message?: string | null;
  result_url: string;
  created_at: string;
  updated_at?: string;
}

export interface UsageSummary {
  owner_id: string;
  year: number;
  month: number;
  characters_used: number;
  total_quota: number;
  quota_remaining: number;
  quota_percentage_used: number;
}

export interface WebhookSubscription {
  id: string;
  url: string;
  event_types: string[];
  secret?: string;
  is_active?: boolean;
  created_at: string;
}

export interface SystemLanguage {
  code: string;
  name: string;
  native_name: string;
  voice_count: number;
  is_default?: boolean;
  default_preview_text?: string;
}

export interface DesignPreviewResponse {
  audio_base64: string;
  content_type: string;
  duration_seconds: number;
  control_instruction: string;
  preview_text: string;
}

export interface SystemAudioFormat {
  format: string;
  mime_type: string;
  sample_rate: number;
  description: string;
}

