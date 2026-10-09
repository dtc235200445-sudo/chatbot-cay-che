import { Cloud, CloudFog, CloudLightning, CloudRain, CloudSun, Snowflake, Sun } from "lucide-react";
import type { LucideIcon } from "lucide-react";

export interface WeatherVisual {
  icon: LucideIcon;
  /** Lớp Tailwind cho nền thẻ thời tiết chính */
  surface: string;
}

/** Chọn biểu tượng và màu nền theo mô tả thời tiết tiếng Việt do backend trả về (mã WMO đã được dịch). */
export function weatherVisual(condition?: string | null): WeatherVisual {
  const text = (condition ?? "").toLowerCase();
  if (text.includes("dông")) {
    return { icon: CloudLightning, surface: "from-slate-700 to-slate-900 text-white" };
  }
  if (text.includes("tuyết")) {
    return { icon: Snowflake, surface: "from-sky-700 to-slate-800 text-white" };
  }
  if (text.includes("mưa")) {
    return { icon: CloudRain, surface: "from-sky-800 to-slate-900 text-white" };
  }
  if (text.includes("sương")) {
    return { icon: CloudFog, surface: "from-slate-600 to-slate-800 text-white" };
  }
  if (text.includes("nhiều mây")) {
    return { icon: Cloud, surface: "from-slate-600 to-emerald-900 text-white" };
  }
  if (text.includes("quang")) {
    return { icon: Sun, surface: "from-amber-700 to-emerald-900 text-white" };
  }
  return { icon: CloudSun, surface: "from-emerald-700 to-emerald-950 text-white" };
}

export function formatNumber(value: number | null | undefined, unit: string, digits = 1): string {
  if (value === null || value === undefined) return `-- ${unit}`.trim();
  return `${Number(value.toFixed(digits))}${unit}`;
}
