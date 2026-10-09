import type {
  UserRegisterRequest,
  UserLoginRequest,
  UserResponse,
  TokenResponse,
  ChatQueryRequest,
  ChatQueryResponse,
  ChatSessionResponse,
  WeatherDataResponse,
  KnowledgeChunkResponse,
  PaginatedResponse,
  TeaDiseaseResponse,
  TeaRegionResponse,
} from "@/types/api";

const API_BASE_URL =
  (import.meta.env["VITE_API_BASE_URL"] as string | undefined) || "http://localhost:8001";
const TOKEN_KEY = "tea_scholar_token";

/** Sự kiện để header kiểm tra lại trạng thái máy chủ ngay khi một yêu cầu thất bại. */
export const API_OFFLINE_EVENT = "tea-api-offline";

function notifyApiOffline(): void {
  if (typeof window !== "undefined") window.dispatchEvent(new Event(API_OFFLINE_EVENT));
}

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const token = getStoredToken();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch {
    // fetch chỉ ném lỗi khi không kết nối được (backend tắt, đang khởi động lại, sai địa chỉ, mất mạng)
    notifyApiOffline();
    throw new Error(
      `Không kết nối được máy chủ (${API_BASE_URL}). Hãy kiểm tra backend đang chạy rồi thử lại.`,
    );
  }

  if (response.status === 401) {
    clearStoredToken();
  }

  if (!response.ok) {
    let errorDetail = `HTTP Error ${response.status}: ${response.statusText}`;
    try {
      const errData = await response.json();
      if (errData?.detail) {
        errorDetail =
          typeof errData.detail === "string" ? errData.detail : JSON.stringify(errData.detail);
      }
    } catch {
      // Ignore JSON parse error if response body is empty
    }
    throw new Error(errorDetail);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const apiClient = {
  health: (): Promise<{ status: string }> => request<{ status: string }>("/api/v1/health"),

  auth: {
    register: (data: UserRegisterRequest): Promise<UserResponse> =>
      request<UserResponse>("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    login: (data: UserLoginRequest): Promise<TokenResponse> =>
      request<TokenResponse>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    me: (): Promise<UserResponse> => request<UserResponse>("/api/v1/auth/me"),
  },

  chat: {
    query: (data: ChatQueryRequest): Promise<ChatQueryResponse> =>
      request<ChatQueryResponse>("/api/v1/chat/query", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    getSessions: (): Promise<ChatSessionResponse[]> =>
      request<ChatSessionResponse[]>("/api/v1/chat/sessions"),
    getSession: (sessionId: number): Promise<ChatSessionResponse> =>
      request<ChatSessionResponse>(`/api/v1/chat/sessions/${sessionId}`),
    deleteSession: (sessionId: number): Promise<void> =>
      request<void>(`/api/v1/chat/sessions/${sessionId}`, { method: "DELETE" }),
  },

  weather: {
    getRegions: (): Promise<TeaRegionResponse[]> =>
      request<TeaRegionResponse[]>("/api/v1/weather/regions"),
    getLive: (region: string): Promise<WeatherDataResponse> =>
      request<WeatherDataResponse>(`/api/v1/weather/live?region=${encodeURIComponent(region)}`),
  },

  knowledge: {
    /** Gợi ý cụm từ bắt đầu bằng phần đã gõ (autocomplete). */
    suggest: async (q: string, limit = 8): Promise<string[]> => {
      const res = await request<{ suggestions: { text: string; count: number }[] }>(
        `/api/v1/knowledge/suggest?q=${encodeURIComponent(q)}&limit=${limit}`,
      );
      return res.suggestions.map((item) => item.text);
    },
    /** Tổng số đoạn tri thức hiện có (lấy từ trường total của danh sách phân trang). */
    count: async (): Promise<number> =>
      (await request<PaginatedResponse<KnowledgeChunkResponse>>("/api/v1/knowledge?page_size=1"))
        .total,
    search: (
      q: string,
      page = 1,
      pageSize = 20,
    ): Promise<PaginatedResponse<KnowledgeChunkResponse>> =>
      request<PaginatedResponse<KnowledgeChunkResponse>>(
        `/api/v1/knowledge/search?q=${encodeURIComponent(q)}&page=${page}&page_size=${pageSize}`,
      ),
  },

  documents: {
    /** Tổng số tài liệu nguồn. */
    count: async (): Promise<number> =>
      (await request<PaginatedResponse<{ id: number }>>("/api/v1/documents?page_size=1")).total,
  },

  diseases: {
    list: (pageSize = 12): Promise<PaginatedResponse<TeaDiseaseResponse>> =>
      request<PaginatedResponse<TeaDiseaseResponse>>(`/api/v1/diseases?page_size=${pageSize}`),
  },
};
