import { useEffect, useState } from "react";
import { API_OFFLINE_EVENT, apiClient } from "@/lib/api-client";

export type ApiStatus = "checking" | "online" | "offline";

const POLL_INTERVAL_MS = 20_000;

/**
 * Kiểm tra backend còn hoạt động hay không để hiển thị trạng thái thật trên header.
 * Kiểm tra định kỳ, khi cửa sổ được focus lại, khi mạng thay đổi và ngay khi một yêu cầu API thất bại.
 */
export function useApiStatus(): ApiStatus {
  const [status, setStatus] = useState<ApiStatus>("checking");

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        await apiClient.health();
        if (!cancelled) setStatus("online");
      } catch {
        if (!cancelled) setStatus("offline");
      }
    };
    void check();
    const timer = setInterval(check, POLL_INTERVAL_MS);
    const onOffline = () => setStatus("offline");
    window.addEventListener("focus", check);
    window.addEventListener("online", check);
    window.addEventListener(API_OFFLINE_EVENT, onOffline);
    return () => {
      cancelled = true;
      clearInterval(timer);
      window.removeEventListener("focus", check);
      window.removeEventListener("online", check);
      window.removeEventListener(API_OFFLINE_EVENT, onOffline);
    };
  }, []);

  return status;
}
