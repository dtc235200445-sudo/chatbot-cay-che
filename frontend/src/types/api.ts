export interface UserRegisterRequest {
  username: string;
  email: string;
  password: string;
  full_name?: string | undefined;
}

export interface UserLoginRequest {
  username_or_email: string;
  password: string;
}

export interface UserResponse {
  id: number;
  username: string;
  email: string;
  full_name?: string | null;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserResponse;
}

export interface ChatQueryRequest {
  session_id?: number | null;
  message: string;
}

export interface ChatSourceItem {
  chunk_id: string;
  title: string;
  source: string;
  similarity_score: number;
}

export interface ChatQueryResponse {
  session_id: number;
  message_id: number;
  role: "assistant";
  answer: string;
  sources: ChatSourceItem[];
  created_at: string;
}

export interface ChatMessageResponse {
  id: number;
  session_id: number;
  role: string;
  content: string;
  sources_json?: string | null;
  created_at: string;
}

export interface ChatSessionResponse {
  id: number;
  user_id?: number | null;
  title: string;
  created_at: string;
  updated_at: string;
  messages?: ChatMessageResponse[];
}

export interface WeatherDataResponse {
  id: number;
  region: string;
  latitude?: number | null;
  longitude?: number | null;
  temperature?: number | null;
  humidity?: number | null;
  rainfall?: number | null;
  wind_speed?: number | null;
  weather_condition?: string | null;
  recorded_at?: string | null;
  created_at: string;
}

export interface KnowledgeChunkResponse {
  id: number;
  chunk_id: string;
  document_id: number;
  title: string;
  content: string;
  source: string;
  source_type: string;
  category: string;
  topic?: string | null;
  disease?: string | null;
  language: string;
  region?: string | null;
  section?: string | null;
  page?: number | null;
  year?: number | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface TeaRegionResponse {
  name: string;
  province: string;
  latitude: number;
  longitude: number;
  area_ha?: number | null;
  altitude_m?: number | null;
}

export interface TeaDiseaseResponse {
  id: number;
  name: string;
  scientific_name?: string | null;
  symptoms?: string | null;
  causes?: string | null;
  prevention?: string | null;
  treatment?: string | null;
  severity?: string | null;
}
