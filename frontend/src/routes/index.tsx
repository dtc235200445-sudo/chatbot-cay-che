import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowRight,
  BookOpenCheck,
  Bug,
  Coffee,
  Droplets,
  Leaf,
  MapPin,
  Mountain,
  Quote,
  Scissors,
  SearchCheck,
  ShieldCheck,
  Sprout,
  Thermometer,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { IconBadge, SectionHeading } from "@/components/common/page-elements";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import teaCulture from "@/assets/tea-culture.jpg";
import teaHarvest from "@/assets/tea-harvest.jpg";
import teaHero from "@/assets/tea-hero.jpg";
import { apiClient } from "@/lib/api-client";
import { formatNumber, weatherVisual } from "@/lib/weather";
import type { TeaDiseaseResponse, WeatherDataResponse } from "@/types/api";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Tea Scholar — Trợ lý tri thức cây chè Việt Nam" },
      {
        name: "description",
        content:
          "Hỏi đáp về kỹ thuật trồng, chăm sóc, sâu bệnh hại và chế biến chè Việt Nam. Câu trả lời có trích dẫn nguồn và thời tiết trực tiếp các vùng chè.",
      },
      { property: "og:title", content: "Tea Scholar — Trợ lý tri thức cây chè Việt Nam" },
      {
        property: "og:description",
        content: "Trợ lý AI trả lời dựa trên tài liệu kỹ thuật chè, có trích dẫn nguồn.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Index,
});

const quickQuestions = [
  "Bệnh thối búp có triệu chứng gì?",
  "Kỹ thuật đốn chè kinh doanh",
  "Thời tiết Thái Nguyên hôm nay",
];

// Các câu hỏi đều nằm trong cơ sở tri thức (đã kiểm tra bằng bộ đánh giá RAG)
const topics: { icon: LucideIcon; title: string; hint: string; question: string }[] = [
  {
    icon: Bug,
    title: "Sâu bệnh hại",
    hint: "Nhận biết triệu chứng và cách phòng trừ",
    question: "Bệnh thối búp trên cây chè có triệu chứng gì?",
  },
  {
    icon: Sprout,
    title: "Bón phân",
    hint: "Lượng phân và thời điểm bón theo giai đoạn",
    question: "Lượng phân bón cho chè kinh doanh",
  },
  {
    icon: Scissors,
    title: "Đốn chè",
    hint: "Đốn phớt, đốn lửng, đốn trẻ lại",
    question: "Đốn chè kinh doanh thực hiện như thế nào?",
  },
  {
    icon: Leaf,
    title: "Hái chè",
    hint: "Hái bằng tay, hái bằng máy, mùa khô hạn",
    question: "Kỹ thuật hái chè bằng tay",
  },
  {
    icon: Mountain,
    title: "Giống và trồng mới",
    hint: "Chọn giống, mật độ, thời vụ trồng",
    question: "Nên chọn giống chè nào cho vùng núi cao?",
  },
  {
    icon: Coffee,
    title: "Chế biến chè xanh",
    hint: "Diệt men, vò, sao khô, bảo quản",
    question: "Quy trình chế biến chè xanh gồm những bước nào?",
  },
];

const steps: { icon: LucideIcon; title: string; text: string }[] = [
  {
    icon: SearchCheck,
    title: "Truy xuất đúng đoạn tri thức",
    text: "Câu hỏi được so khớp với cơ sở tri thức bằng cả ngữ nghĩa lẫn từ khóa chuyên môn để chọn ra các đoạn liên quan nhất.",
  },
  {
    icon: Quote,
    title: "Trả lời kèm trích dẫn nguồn",
    text: "Mỗi câu trả lời hiển thị các đoạn tài liệu đã dùng, để bạn tự kiểm chứng thay vì tin vào lời của mô hình.",
  },
  {
    icon: ShieldCheck,
    title: "Từ chối khi chưa có thông tin",
    text: "Khi cơ sở tri thức không có nội dung phù hợp, trợ lý nói rõ điều đó thay vì đoán mò.",
  },
];

const weatherRegions = ["Thái Nguyên", "Phú Thọ", "Lâm Đồng", "Mộc Châu"];

/** Số liệu thật từ API; hiển thị "…" khi đang tải và ẩn khi không lấy được. */
function useFacts() {
  const [facts, setFacts] = useState<{ chunks: number; documents: number; regions: number } | null>(
    null,
  );
  useEffect(() => {
    let cancelled = false;
    Promise.all([
      apiClient.knowledge.count(),
      apiClient.documents.count(),
      apiClient.weather.getRegions(),
    ])
      .then(([chunks, documents, regions]) => {
        if (!cancelled) setFacts({ chunks, documents, regions: regions.length });
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);
  return facts;
}

function HeroAsk() {
  const navigate = useNavigate();
  const [text, setText] = useState("");

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const q = text.trim();
    void navigate({ to: "/assistant", search: q ? { q } : {} });
  };

  return (
    <div className="mt-8 max-w-2xl">
      <form
        onSubmit={submit}
        className="flex items-center gap-2 rounded-2xl bg-white/95 p-2 shadow-lift backdrop-blur"
      >
        <input
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder="Đặt câu hỏi về cây chè…"
          maxLength={2000}
          aria-label="Câu hỏi cho trợ lý"
          className="h-12 min-w-0 flex-1 bg-transparent px-4 text-base text-foreground outline-none placeholder:text-muted-foreground"
        />
        <Button type="submit" size="lg" className="h-12 rounded-xl px-5">
          Hỏi trợ lý
          <ArrowRight />
        </Button>
      </form>
      <div className="mt-4 flex flex-wrap gap-2">
        {quickQuestions.map((question) => (
          <Link
            key={question}
            to="/assistant"
            search={{ q: question }}
            className="rounded-full border border-white/30 bg-white/10 px-3.5 py-1.5 text-sm text-white backdrop-blur transition-colors hover:bg-white/20"
          >
            {question}
          </Link>
        ))}
      </div>
    </div>
  );
}

function RegionWeather() {
  const [items, setItems] = useState<(WeatherDataResponse | null)[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    void Promise.allSettled(weatherRegions.map((region) => apiClient.weather.getLive(region))).then(
      (results) => {
        if (cancelled) return;
        setItems(results.map((r) => (r.status === "fulfilled" ? r.value : null)));
      },
    );
    return () => {
      cancelled = true;
    };
  }, []);

  if (items && items.every((item) => item === null)) return null;

  return (
    <section className="mt-20">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <SectionHeading
          eyebrow="Thời tiết trực tiếp"
          title="Điều kiện hôm nay tại các vùng chè"
          description="Số liệu lấy trực tiếp từ Open-Meteo theo tọa độ của từng vùng."
          className="mb-0"
        />
        <Button asChild variant="outline" className="w-fit rounded-full">
          <Link to="/weather">
            Xem chi tiết
            <ArrowRight />
          </Link>
        </Button>
      </div>
      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {weatherRegions.map((region, index) => {
          const data = items?.[index];
          if (!items) return <Skeleton key={region} className="h-40 rounded-2xl" />;
          if (!data) return null;
          const visual = weatherVisual(data.weather_condition);
          return (
            <Link
              key={region}
              to="/weather"
              className={`group relative overflow-hidden rounded-2xl bg-gradient-to-br p-5 shadow-soft transition-transform hover:-translate-y-0.5 ${visual.surface}`}
            >
              <visual.icon
                className="absolute -right-3 -top-3 size-24 text-white/15"
                strokeWidth={1.2}
              />
              <p className="flex items-center gap-1.5 text-sm font-medium text-white/85">
                <MapPin className="size-3.5" />
                {region}
              </p>
              <p className="mt-3 font-display text-4xl font-semibold tabular-nums">
                {formatNumber(data.temperature, "°C", 1)}
              </p>
              <p className="mt-1 text-sm text-white/80">{data.weather_condition}</p>
              <p className="mt-4 flex items-center gap-1.5 text-xs text-white/75">
                <Droplets className="size-3.5" />
                Độ ẩm {formatNumber(data.humidity, "%", 0)}
              </p>
            </Link>
          );
        })}
      </div>
    </section>
  );
}

function DiseaseShowcase() {
  const [diseases, setDiseases] = useState<TeaDiseaseResponse[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    apiClient.diseases
      .list(12)
      .then((res) => {
        if (cancelled) return;
        // Bỏ các lớp tiếng Anh của bộ dữ liệu ảnh, chỉ hiển thị tên tiếng Việt
        setDiseases(
          res.items.filter((d) => !/^[A-Za-z ]+$/.test(d.name) && d.symptoms).slice(0, 6),
        );
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (failed || (diseases && diseases.length === 0)) return null;

  return (
    <section className="mt-20">
      <SectionHeading
        eyebrow="Sâu bệnh hại"
        title="Nhận biết sớm để bảo vệ vườn chè"
        description="Triệu chứng tóm tắt từ danh mục bệnh hại của hệ thống. Bấm để hỏi trợ lý cách phòng trừ chi tiết kèm nguồn."
      />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {diseases === null
          ? Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-44 rounded-2xl" />)
          : diseases.map((disease) => (
              <article
                key={disease.id}
                className="group flex flex-col rounded-2xl border bg-card p-5 shadow-soft transition-all hover:-translate-y-0.5 hover:shadow-lift"
              >
                <IconBadge icon={Bug} />
                <h3 className="mt-4 text-lg font-semibold">{disease.name}</h3>
                <p className="mt-2 line-clamp-3 flex-1 text-sm leading-6 text-muted-foreground">
                  {disease.symptoms}
                </p>
                <Link
                  to="/assistant"
                  search={{ q: `Triệu chứng và cách phòng trừ ${disease.name} trên cây chè` }}
                  className="mt-4 inline-flex w-fit items-center gap-1.5 text-sm font-medium text-primary hover:underline"
                >
                  Hỏi cách phòng trừ
                  <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
                </Link>
              </article>
            ))}
      </div>
    </section>
  );
}

function Index() {
  const facts = useFacts();
  return (
    <div>
      {/* Hero */}
      <section className="relative isolate overflow-hidden">
        <img
          src={teaHero}
          alt="Đồi chè xanh trong sương sớm"
          width={1920}
          height={1024}
          className="absolute inset-0 -z-10 size-full object-cover"
        />
        <div
          className="absolute inset-0 -z-10 bg-gradient-to-r from-emerald-950/90 via-emerald-950/65 to-emerald-950/15"
          aria-hidden
        />
        <div className="mx-auto max-w-6xl px-4 pb-16 pt-14 sm:px-6 sm:pt-20 lg:px-10 lg:pb-24 lg:pt-28">
          <p className="inline-flex items-center gap-2 rounded-full border border-white/25 bg-white/10 px-3.5 py-1.5 text-xs font-medium uppercase tracking-widest text-white/90 backdrop-blur">
            <Leaf className="size-3.5 text-amber" />
            Trợ lý tri thức cây chè Việt Nam
          </p>
          <h1 className="mt-6 max-w-3xl text-4xl font-semibold leading-[1.1] text-white sm:text-6xl">
            Hỏi đáp về cây chè, <span className="text-amber">có nguồn để kiểm chứng</span>
          </h1>
          <p className="mt-5 max-w-xl text-base leading-7 text-white/85 sm:text-lg">
            Trợ lý trả lời dựa trên tài liệu kỹ thuật trồng và chăm sóc chè, kết hợp thời tiết trực
            tiếp từng vùng. Không có thông tin phù hợp, trợ lý sẽ nói rõ.
          </p>
          <HeroAsk />
          {facts && (
            <dl className="mt-12 grid max-w-2xl grid-cols-3 gap-6 border-t border-white/20 pt-6">
              {[
                { value: facts.chunks, label: "đoạn tri thức kỹ thuật" },
                { value: facts.documents, label: "tài liệu nguồn" },
                { value: facts.regions, label: "vùng chè có thời tiết trực tiếp" },
              ].map((fact) => (
                <div key={fact.label}>
                  <dt className="font-display text-3xl font-semibold text-white sm:text-4xl">
                    {fact.value}
                  </dt>
                  <dd className="mt-1 text-xs leading-5 text-white/75 sm:text-sm">{fact.label}</dd>
                </div>
              ))}
            </dl>
          )}
        </div>
      </section>

      <div className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6 lg:px-10">
        {/* Topics */}
        <section>
          <SectionHeading
            eyebrow="Bạn có thể hỏi"
            title="Sáu nhóm chủ đề chính"
            description="Chọn một chủ đề để bắt đầu với câu hỏi mẫu. Trợ lý sẽ mở sẵn cuộc trò chuyện."
          />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {topics.map((topic) => (
              <Link
                key={topic.title}
                to="/assistant"
                search={{ q: topic.question }}
                className="group flex items-start gap-4 rounded-2xl border bg-card p-5 shadow-soft transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-lift"
              >
                <IconBadge icon={topic.icon} />
                <div className="min-w-0 flex-1">
                  <h3 className="text-base font-semibold">{topic.title}</h3>
                  <p className="mt-1 text-sm leading-6 text-muted-foreground">{topic.hint}</p>
                </div>
                <ArrowRight className="mt-1 size-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-1 group-hover:text-primary" />
              </Link>
            ))}
          </div>
        </section>

        <RegionWeather />
        <DiseaseShowcase />

        {/* How it works */}
        <section className="mt-20 overflow-hidden rounded-3xl border bg-card shadow-soft">
          <div className="grid lg:grid-cols-5">
            <div className="p-8 sm:p-10 lg:col-span-3">
              <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-primary">
                <BookOpenCheck className="size-4" />
                Cách trợ lý hoạt động
              </p>
              <h2 className="mt-3 text-2xl font-semibold sm:text-3xl">
                Trả lời dựa trên tài liệu, không dựa trên phỏng đoán
              </h2>
              <ol className="mt-8 space-y-6">
                {steps.map((step, index) => (
                  <li key={step.title} className="flex gap-4">
                    <div className="grid size-10 shrink-0 place-items-center rounded-full bg-primary font-display text-base font-semibold text-primary-foreground">
                      {index + 1}
                    </div>
                    <div>
                      <h3 className="flex items-center gap-2 font-semibold">
                        <step.icon className="size-4 text-primary" />
                        {step.title}
                      </h3>
                      <p className="mt-1 text-sm leading-6 text-muted-foreground">{step.text}</p>
                    </div>
                  </li>
                ))}
              </ol>
            </div>
            <div className="relative min-h-64 lg:col-span-2">
              <img
                src={teaHarvest}
                alt="Bàn tay hái búp chè non"
                width={1024}
                height={768}
                loading="lazy"
                className="absolute inset-0 size-full object-cover"
              />
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="relative isolate mt-20 overflow-hidden rounded-3xl">
          <img
            src={teaCulture}
            alt=""
            width={1024}
            height={768}
            loading="lazy"
            className="absolute inset-0 -z-10 size-full object-cover"
          />
          <div className="absolute inset-0 -z-10 bg-emerald-950/80" aria-hidden />
          <div className="flex flex-col items-start justify-between gap-6 p-8 sm:p-12 md:flex-row md:items-center">
            <div className="max-w-xl">
              <h2 className="text-2xl font-semibold text-white sm:text-3xl">
                Có câu hỏi về vườn chè của bạn?
              </h2>
              <p className="mt-3 text-sm leading-6 text-white/80 sm:text-base">
                Hỏi trợ lý ngay, hoặc tra cứu trực tiếp trong cơ sở tri thức để đọc nguyên văn tài
                liệu.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button
                asChild
                size="lg"
                className="rounded-full bg-amber text-amber-foreground hover:bg-amber/90"
              >
                <Link to="/assistant">
                  Hỏi trợ lý
                  <ArrowRight />
                </Link>
              </Button>
              <Button
                asChild
                size="lg"
                variant="outline"
                className="rounded-full border-white/40 bg-white/10 text-white hover:bg-white/20 hover:text-white"
              >
                <Link to="/search">Tra cứu tri thức</Link>
              </Button>
            </div>
          </div>
        </section>

        <footer className="mt-16 flex flex-col items-center justify-between gap-2 border-t pt-8 text-xs text-muted-foreground sm:flex-row">
          <span className="flex items-center gap-2">
            <Thermometer className="size-3.5" />
            Thông tin mang tính tham khảo, không thay thế tư vấn của cán bộ kỹ thuật.
          </span>
          <span>Tea Scholar — đồ án tốt nghiệp</span>
        </footer>
      </div>
    </div>
  );
}
