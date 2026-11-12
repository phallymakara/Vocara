/**
 * API Client Controller for Vocara Platform.
 * Encapsulates low-level HTTP communication and error formatting.
 */

import type {
  ApiKeyCreated,
  ApiKeyItem,
  AuthSessionResponse,
  DesignPreviewResponse,
  JobItem,
  SystemAudioFormat,
  SystemLanguage,
  TtsRequestPayload,
  UsageSummary,
  UserProfile,
  VoiceItem,
  WebhookSubscription,
} from "@/models/types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";
const API_KEY_STORAGE_KEY = "vocara_active_api_key";
const AUTH_TOKEN_STORAGE_KEY = "vocara_session_token";

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public fieldErrors?: Record<string, string>
  ) {
    super(message);
    this.name = "ApiError";
  }
}

class VocaraApiClient {
  private activeApiKey: string | null = null;
  private authToken: string | null = null;

  constructor() {
    this.activeApiKey = localStorage.getItem(API_KEY_STORAGE_KEY);
    this.authToken = localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
  }

  getApiKey(): string | null {
    return this.activeApiKey;
  }

  setApiKey(key: string | null): void {
    this.activeApiKey = key;
    if (key) {
      localStorage.setItem(API_KEY_STORAGE_KEY, key);
    } else {
      localStorage.removeItem(API_KEY_STORAGE_KEY);
    }
  }

  getAuthToken(): string | null {
    return this.authToken;
  }

  setAuthToken(token: string | null): void {
    this.authToken = token;
    if (token) {
      localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
    } else {
      localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
    }
  }

  private getHeaders(extraHeaders: Record<string, string> = {}): Record<string, string> {
    const headers: Record<string, string> = { ...extraHeaders };
    if (this.authToken) {
      headers["Authorization"] = `Bearer ${this.authToken}`;
    } else if (this.activeApiKey) {
      headers["Authorization"] = `Bearer ${this.activeApiKey}`;
    }
    return headers;
  }

  private async handleResponse<T>(res: Response): Promise<T> {
    if (!res.ok) {
      let errorMessage = "An unexpected error occurred. Please try again.";
      const fieldErrors: Record<string, string> = {};

      try {
        const data = await res.json();
        if (data && typeof data === "object") {
          if (Array.isArray(data.detail)) {
            for (const item of data.detail) {
              const field = item.loc ? item.loc[item.loc.length - 1] : "general";
              fieldErrors[String(field)] = item.msg || "Invalid value";
            }
            errorMessage = "Please check the entered values.";
          } else if (data.error && typeof data.error === "object") {
            if (Array.isArray(data.error.fields)) {
              for (const f of data.error.fields) {
                if (f.field && f.message) {
                  fieldErrors[String(f.field)] = String(f.message);
                }
              }
            }
            if (data.error.message) {
              errorMessage = data.error.message;
            }
          } else if (typeof data.detail === "string") {
            if (data.detail.toLowerCase() === "not found") {
              errorMessage = "The requested service is currently unavailable or could not be found.";
            } else {
              errorMessage = data.detail;
            }
          } else if (data.message) {
            errorMessage = data.message;
          }
        }
      } catch {
        // Fallback for non-JSON responses
      }

      if (res.status === 401) {
        if (this.authToken) {
          this.setAuthToken(null);
          window.dispatchEvent(new CustomEvent("vocara:unauthorized"));
        } else {
          this.setApiKey(null);
        }
        if (errorMessage === "An unexpected error occurred. Please try again.") {
          errorMessage = "Please sign in to continue.";
        }
      } else if (res.status === 403) {
        errorMessage = "You do not have access to this resource.";
      } else if (res.status === 404 && errorMessage === "An unexpected error occurred. Please try again.") {
        errorMessage = "The requested service is currently unavailable.";
      } else if (res.status === 429 && errorMessage === "An unexpected error occurred. Please try again.") {
        errorMessage = "Monthly quota or rate limit reached. Please wait a moment.";
      }

      throw new ApiError(errorMessage, res.status, fieldErrors);
    }

    return (await res.json()) as T;
  }

  async registerUser(name: string, email: string, password: string): Promise<AuthSessionResponse> {
    const res = await fetch(`${BASE_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, password }),
    });
    return this.handleResponse<AuthSessionResponse>(res);
  }

  async loginUser(email: string, password: string): Promise<AuthSessionResponse> {
    const res = await fetch(`${BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    return this.handleResponse<AuthSessionResponse>(res);
  }

  async getCurrentUser(): Promise<UserProfile> {
    const res = await fetch(`${BASE_URL}/auth/me`, {
      headers: this.getHeaders(),
    });
    return this.handleResponse<UserProfile>(res);
  }

  getGoogleLoginUrl(): string {
    return `${BASE_URL}/auth/google/login`;
  }

  async getHealth(): Promise<{ status: string; service: string; environment: string }> {
    const res = await fetch("/health");
    return this.handleResponse(res);
  }

  async getLanguages(): Promise<SystemLanguage[]> {
    const res = await fetch(`${BASE_URL}/system/languages`, {
      headers: this.getHeaders(),
    });
    return this.handleResponse<SystemLanguage[]>(res);
  }

  async getFormats(): Promise<SystemAudioFormat[]> {
    const res = await fetch(`${BASE_URL}/system/formats`, {
      headers: this.getHeaders(),
    });
    return this.handleResponse<SystemAudioFormat[]>(res);
  }

  async listKeys(): Promise<ApiKeyItem[]> {
    const res = await fetch(`${BASE_URL}/keys`, {
      headers: this.getHeaders(),
    });
    return this.handleResponse<ApiKeyItem[]>(res);
  }

  async createKey(name: string): Promise<ApiKeyCreated> {
    const res = await fetch(`${BASE_URL}/keys`, {
      method: "POST",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ name }),
    });
    return this.handleResponse<ApiKeyCreated>(res);
  }

  async updateKeyName(id: string, name: string): Promise<ApiKeyItem> {
    const res = await fetch(`${BASE_URL}/keys/${id}`, {
      method: "PATCH",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ name }),
    });
    return this.handleResponse<ApiKeyItem>(res);
  }

  async revokeKey(id: string): Promise<void> {
    const res = await fetch(`${BASE_URL}/keys/${id}/revoke`, {
      method: "POST",
      headers: this.getHeaders(),
    });
    if (!res.ok) {
      await this.handleResponse(res);
    }
  }

  async deleteKey(id: string): Promise<void> {
    const res = await fetch(`${BASE_URL}/keys/${id}?permanent=true`, {
      method: "DELETE",
      headers: this.getHeaders(),
    });
    if (!res.ok) {
      await this.handleResponse(res);
    }
  }

  async listVoices(language?: string): Promise<VoiceItem[]> {
    const query = language ? `?language=${encodeURIComponent(language)}` : "";
    const res = await fetch(`${BASE_URL}/voices${query}`, {
      headers: this.getHeaders(),
    });
    return this.handleResponse<VoiceItem[]>(res);
  }

  async cloneVoice(formData: FormData): Promise<VoiceItem> {
    const res = await fetch(`${BASE_URL}/voices/clone`, {
      method: "POST",
      headers: this.getHeaders(),
      body: formData,
    });
    return this.handleResponse<VoiceItem>(res);
  }

  async previewDesignVoice(payload: {
    description?: string;
    base_voice_id?: string;
    gender?: string;
    pitch?: number;
    speed?: number;
    emotion?: string;
    style?: string;
    preview_text?: string;
    extra_modifiers?: Record<string, unknown>;
  }): Promise<DesignPreviewResponse> {
    const res = await fetch(`${BASE_URL}/voices/design/preview`, {
      method: "POST",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });
    return this.handleResponse<DesignPreviewResponse>(res);
  }

  async designVoice(payload: {
    name: string;
    description?: string;
    base_voice_id?: string;
    gender?: string;
    pitch?: number;
    speed?: number;
    emotion?: string;
    style?: string;
    preview_text?: string;
    preview_audio_base64?: string;
    extra_modifiers?: Record<string, unknown>;
  }): Promise<VoiceItem> {
    const res = await fetch(`${BASE_URL}/voices/design`, {
      method: "POST",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });
    return this.handleResponse<VoiceItem>(res);
  }

  async updateVoice(
    voiceId: string,
    payload: {
      name?: string;
      description?: string;
      visibility?: "public" | "private";
      modifiers?: Record<string, unknown>;
    }
  ): Promise<VoiceItem> {
    const res = await fetch(`${BASE_URL}/voices/${voiceId}`, {
      method: "PATCH",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });
    return this.handleResponse<VoiceItem>(res);
  }

  async deleteVoice(voiceId: string): Promise<void> {
    const res = await fetch(`${BASE_URL}/voices/${voiceId}`, {
      method: "DELETE",
      headers: this.getHeaders(),
    });
    if (!res.ok) {
      await this.handleResponse(res);
    }
  }

  getVoicePreviewUrl(voiceId: string): string {
    const url = `${BASE_URL}/voices/${voiceId}/preview`;
    const params = new URLSearchParams();
    const credential = this.authToken || this.activeApiKey;
    if (credential) {
      params.set("api_key", credential);
    }
    params.set("t", String(Date.now()));
    return `${url}?${params.toString()}`;
  }

  async synthesizeSpeech(
    payload: TtsRequestPayload,
    signal?: AbortSignal
  ): Promise<{ type: "stream"; audioBlob: Blob; duration: number } | { type: "job"; job: JobItem }> {
    const res = await fetch(`${BASE_URL}/tts`, {
      method: "POST",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
      signal,
    });

    if (res.status === 200) {
      const audioBlob = await res.blob();
      const durationHeader = res.headers.get("X-Audio-Duration");
      const duration = durationHeader ? parseFloat(durationHeader) : 0;
      return { type: "stream", audioBlob, duration };
    }

    if (res.status === 202) {
      const job = (await res.json()) as JobItem;
      return { type: "job", job };
    }

    return this.handleResponse(res);
  }

  async getJob(id: string, signal?: AbortSignal): Promise<JobItem> {
    const res = await fetch(`${BASE_URL}/jobs/${id}`, {
      headers: this.getHeaders(),
      signal,
    });
    return this.handleResponse<JobItem>(res);
  }

  async getJobResultBlob(id: string, signal?: AbortSignal): Promise<Blob> {
    const res = await fetch(`${BASE_URL}/jobs/${id}/result`, {
      headers: this.getHeaders(),
      signal,
    });
    if (!res.ok) {
      await this.handleResponse(res);
    }
    return await res.blob();
  }

  async getUsage(year?: number, month?: number): Promise<UsageSummary> {
    const params = new URLSearchParams();
    if (year !== undefined) params.set("year", String(year));
    if (month !== undefined) params.set("month", String(month));
    params.set("tz_offset", String(-new Date().getTimezoneOffset()));
    const qs = params.toString();
    const res = await fetch(`${BASE_URL}/usage${qs ? `?${qs}` : ""}`, {
      headers: this.getHeaders(),
    });
    return this.handleResponse<UsageSummary>(res);
  }

  async listWebhooks(): Promise<WebhookSubscription[]> {
    const res = await fetch(`${BASE_URL}/webhooks`, {
      headers: this.getHeaders(),
    });
    return this.handleResponse<WebhookSubscription[]>(res);
  }

  async createWebhook(url: string, event_types: string[]): Promise<WebhookSubscription> {
    const res = await fetch(`${BASE_URL}/webhooks`, {
      method: "POST",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ url, event_types }),
    });
    return this.handleResponse<WebhookSubscription>(res);
  }

  async deleteWebhook(id: string): Promise<void> {
    const res = await fetch(`${BASE_URL}/webhooks/${id}`, {
      method: "DELETE",
      headers: this.getHeaders(),
    });
    if (!res.ok) {
      await this.handleResponse(res);
    }
  }
}

export const apiClient = new VocaraApiClient();

