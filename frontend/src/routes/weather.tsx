import { createFileRoute, Link } from "@tanstack/react-router";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Clock,
  CloudRain,
  Droplets,
  MapPin,
  RefreshCw,
  TriangleAlert,
  Wind,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { PageHeader } from "@/components/common/page-elements";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { apiClient } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import { formatNumber, weatherVisual } from "@/lib/weather";
import type { WeatherDataResponse } from "@/types/api";

// Danh sách dự phòng khi chưa lấy được /weather/regions; nguồn chính là data/tea_regions.json qua API
const FALLBACK_REGIONS = [
  "Thái Nguyên",
  "Phú Thọ",
  "Lâm Đồng",
  "Bảo Lộc",
  "Đà Lạt",
  "Lai Châu",
  "Sơn La",
  "Mộc Châu",
  "Hà Giang",
  "Yên Bái",
  "Tuyên Quang",
  "Nghệ An",
];

export const Route = createFileRoute("/weather")({
  head: () => ({
    meta: [
      { title: "Thời tiết vùng chè — Tea Scholar" },
      {
        name: "description",
        content:
          "Thời tiết hiện tại tại các vùng trồng chè Việt Nam, đối chiếu với ngưỡng sinh trưởng.",
      },
      { property: "og:title", content: "Thời tiết vùng chè — Tea Scholar" },
      {
        property: "og:description",
        content: "Thời tiết trực tiếp cho các vùng trồng chè chính.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: WeatherPage,
});

type Verdict = "good" | "watch" | "bad";

interface Assessment {
  verdict: Verdict;
  label: string;
  detail: string;
}

/**
 * Ngưỡng sinh trưởng lấy từ cơ sở tri thức:
 * - Nhiệt độ 18–28°C thích hợp; dưới 13°C hoặc trên 30°C sinh trưởng yếu (TL1, tea_000053).
 * - Độ ẩm không khí 75–80% phù hợp (Quyết định Lai Châu, tea_000121).
 */
function assessTemperature(value: number): Assessment {
  if (value >= 18 && value <= 28) {
    return { verdict: "good", label: "Trong khoảng thích hợp", detail: "18–28°C theo TL1" };
  }
  if (value < 13 || value > 30) {
    return {
      verdict: "bad",
      label: value < 13 ? "Dưới ngưỡng sinh trưởng" : "Trên ngưỡng sinh trưởng",
      detail: "TL1: dưới 13°C hoặc trên 30°C cây sinh trưởng yếu",
    };
  }
  return {
    verdict: "watch",
    label: "Gần ngưỡng giới hạn",
    detail: "Ngoài 18–28°C nhưng chưa tới 13/30°C",
  };
}

function assessHumidity(value: number): Assessment {
  if (value >= 75 && value <= 80) {
    return {
      verdict: "good",
      label: "Trong khoảng phù hợp",
      detail: "75–80% theo Quyết định Lai Châu",
    };
  }
  if (value > 80) {
    return {
      verdict: "watch",
      label: "Cao hơn khoảng phù hợp",
      detail: "TL1: ẩm độ không khí cao, trời âm u dễ phát sinh sâu bệnh",
    };
  }
  return { verdict: "watch", label: "Thấp hơn khoảng phù hợp", detail: "Khoảng phù hợp là 75–80%" };
}

const VERDICT_STYLE: Record<Verdict, { icon: LucideIcon; className: string }> = {
  good: { icon: CheckCircle2, className: "text-emerald-700 dark:text-emerald-400" },
  watch: { icon: TriangleAlert, className: "text-amber-700 dark:text-amber-400" },
  bad: { icon: TriangleAlert, className: "text-destructive" },
};

/** Thanh hiển thị giá trị hiện tại so với khoảng thích hợp. */
function RangeGauge({
  value,
  min,
  max,
  idealFrom,
  idealTo,
  unit,
}: {
  value: number;
  min: number;
  max: number;
  idealFrom: number;
  idealTo: number;
  unit: string;
}) {
  const pct = (v: number) => Math.min(100, Math.max(0, ((v - min) / (max - min)) * 100));
  return (
    <div className="mt-4">
      <div className="relative h-2.5 rounded-full bg-muted">
        <div
          className="absolute inset-y-0 rounded-full bg-emerald-500/35"
          style={{ left: `${pct(idealFrom)}%`, width: `${pct(idealTo) - pct(idealFrom)}%` }}
        />
        <div
          className="absolute top-1/2 size-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-background bg-primary shadow-soft"
          style={{ left: `${pct(value)}%` }}
        />
      </div>
      <div className="mt-1.5 flex justify-between text-[11px] text-muted-foreground">
        <span>
          {min}
          {unit}
        </span>
        <span>
          {max}
          {unit}
        </span>
      </div>
    </div>
  );
}

function AssessmentCard({
  title,
  value,
  unit,
  assessment,
  gauge,
}: {
  title: string;
  value: number | null | undefined;
  unit: string;
  assessment: Assessment | null;
  gauge?: { min: number; max: number; idealFrom: number; idealTo: number };
}) {
  const style = assessment ? VERDICT_STYLE[assessment.verdict] : null;
  return (
    <div className="rounded-2xl border bg-card p-5 shadow-soft">
      <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {title}
      </p>
      <p className="mt-2 font-display text-3xl font-semibold tabular-nums">
        {value === null || value === undefined ? "--" : `${Number(value.toFixed(1))}${unit}`}
      </p>
      {assessment && style && (
        <p className={cn("mt-2 flex items-center gap-1.5 text-sm font-medium", style.className)}>
          <style.icon className="size-4" />
          {assessment.label}
        </p>
      )}
      {gauge && value !== null && value !== undefined && (
        <RangeGauge value={value} unit={unit} {...gauge} />
      )}
      {assessment && (
        <p className="mt-3 text-xs leading-5 text-muted-foreground">{assessment.detail}</p>
      )}
    </div>
  );
}

function Metric({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: string }) {
  return (
    <div className="rounded-xl bg-white/10 p-4 backdrop-blur-sm">
      <Icon className="size-5 text-white/80" />
      <dt className="mt-3 text-xs text-white/70">{label}</dt>
      <dd className="mt-0.5 text-lg font-semibold tabular-nums">{value}</dd>
    </div>
  );
}

function WeatherPage() {
  const [region, setRegion] = useState("Thái Nguyên");
  const [regionNames, setRegionNames] = useState<string[]>(FALLBACK_REGIONS);
  const [data, setData] = useState<WeatherDataResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);

  const load = useCallback(async (name: string) => {
    const id = ++requestId.current;
    setLoading(true);
    setError(null);
    try {
      const result = await apiClient.weather.getLive(name);
      if (id === requestId.current) setData(result);
    } catch (err: unknown) {
      if (id === requestId.current) {
        setError(err instanceof Error ? err.message : "Không thể lấy dữ liệu thời tiết trực tiếp.");
      }
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(region);
  }, [region, load]);

  useEffect(() => {
    apiClient.weather
      .getRegions()
      .then((list) => {
        if (list.length > 0) setRegionNames(list.map((r) => r.name));
      })
      .catch(() => undefined); // giữ danh sách dự phòng
  }, []);

  const visual = weatherVisual(data?.weather_condition);
  const recordedAt = data?.recorded_at
    ? new Date(data.recorded_at).toLocaleString("vi-VN", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : null;

  const tempAssessment = data?.temperature != null ? assessTemperature(data.temperature) : null;
  const humidityAssessment = data?.humidity != null ? assessHumidity(data.humidity) : null;

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6 lg:px-10 lg:py-14">
      <PageHeader
        eyebrow="Thời tiết nông nghiệp"
        title="Thời tiết vùng chè"
        subtitle="Số liệu hiện tại theo tọa độ từng vùng (Open-Meteo), đối chiếu với ngưỡng sinh trưởng nêu trong tài liệu kỹ thuật."
        action={
          <Button
            variant="outline"
            className="rounded-full"
            onClick={() => void load(region)}
            disabled={loading}
          >
            <RefreshCw className={cn(loading && "animate-spin")} />
            Cập nhật
          </Button>
        }
      />

      <div className="-mx-1 mb-8 flex flex-wrap gap-2" role="tablist" aria-label="Chọn vùng chè">
        {regionNames.map((name) => (
          <button
            key={name}
            type="button"
            role="tab"
            aria-selected={name === region}
            onClick={() => setRegion(name)}
            className={cn(
              "flex items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-sm transition-colors",
              name === region
                ? "border-primary bg-primary text-primary-foreground shadow-soft"
                : "bg-card text-foreground/80 hover:border-primary/40 hover:bg-tea-soft",
            )}
          >
            {name === region && <MapPin className="size-3.5" />}
            {name}
          </button>
        ))}
      </div>

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="size-4" />
          <AlertDescription className="flex flex-wrap items-center justify-between gap-2">
            <span>{error}</span>
            <Button size="sm" variant="outline" onClick={() => void load(region)}>
              Thử lại
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {!data && loading ? (
        <div className="space-y-4">
          <Skeleton className="h-64 rounded-3xl" />
          <div className="grid gap-4 sm:grid-cols-2">
            <Skeleton className="h-52 rounded-2xl" />
            <Skeleton className="h-52 rounded-2xl" />
          </div>
        </div>
      ) : data ? (
        <div className={cn("transition-opacity", loading && "opacity-60")}>
          <section
            className={`relative overflow-hidden rounded-3xl bg-gradient-to-br p-6 shadow-lift sm:p-8 ${visual.surface}`}
          >
            <visual.icon
              className="absolute -right-6 -top-6 size-56 text-white/10"
              strokeWidth={1}
            />
            <div className="relative">
              <p className="flex items-center gap-2 text-sm font-medium text-white/85">
                <MapPin className="size-4" />
                {data.region}
              </p>
              <div className="mt-4 flex flex-wrap items-end gap-x-6 gap-y-2">
                <p className="font-display text-7xl font-semibold leading-none tabular-nums sm:text-8xl">
                  {formatNumber(data.temperature, "°", 1)}
                </p>
                <div className="pb-2">
                  <p className="text-xl font-medium">{data.weather_condition ?? "Không rõ"}</p>
                  {recordedAt && (
                    <p className="mt-1 flex items-center gap-1.5 text-xs text-white/75">
                      <Clock className="size-3.5" />
                      Cập nhật {recordedAt}
                    </p>
                  )}
                </div>
              </div>
              <dl className="mt-8 grid grid-cols-3 gap-3">
                <Metric icon={Droplets} label="Độ ẩm" value={formatNumber(data.humidity, "%", 0)} />
                <Metric
                  icon={CloudRain}
                  label="Lượng mưa"
                  value={formatNumber(data.rainfall, " mm", 1)}
                />
                <Metric
                  icon={Wind}
                  label="Tốc độ gió"
                  value={formatNumber(data.wind_speed, " m/s", 1)}
                />
              </dl>
            </div>
          </section>

          <section className="mt-8">
            <h2 className="font-display text-xl font-semibold">Đối chiếu với ngưỡng sinh trưởng</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Ngưỡng lấy từ tài liệu kỹ thuật trong cơ sở tri thức, không phải khuyến cáo riêng cho
              vườn của bạn.
            </p>
            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <AssessmentCard
                title="Nhiệt độ không khí"
                value={data.temperature}
                unit="°C"
                assessment={tempAssessment}
                gauge={{ min: 0, max: 40, idealFrom: 18, idealTo: 28 }}
              />
              <AssessmentCard
                title="Độ ẩm không khí"
                value={data.humidity}
                unit="%"
                assessment={humidityAssessment}
                gauge={{ min: 30, max: 100, idealFrom: 75, idealTo: 80 }}
              />
            </div>
            <p className="mt-4 text-xs leading-5 text-muted-foreground">
              Các tài liệu có thể nêu khoảng khác nhau (ví dụ Quyết định Lai Châu nêu nhiệt độ
              15–20°C). Nguồn: chunk tea_000053 (TL1), tea_000121 và tea_000122 (Quyết định 450 Lai
              Châu).
            </p>
          </section>

          <section className="mt-8 flex flex-col items-start justify-between gap-4 rounded-2xl border bg-tea-soft p-6 sm:flex-row sm:items-center">
            <div>
              <h2 className="font-display text-lg font-semibold">
                Điều kiện này có thuận lợi cho sâu bệnh không?
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Hỏi trợ lý để kết hợp thời tiết {data.region} với tài liệu về bệnh hại.
              </p>
            </div>
            <Button asChild className="shrink-0 rounded-full">
              <Link
                to="/assistant"
                search={{
                  q: `Thời tiết ${data.region} hiện tại có điều kiện thuận lợi cho bệnh thối búp không?`,
                }}
              >
                Hỏi trợ lý
                <ArrowRight />
              </Link>
            </Button>
          </section>
        </div>
      ) : null}
    </div>
  );
}
