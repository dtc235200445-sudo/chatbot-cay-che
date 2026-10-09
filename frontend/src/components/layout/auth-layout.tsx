import { Link } from "@tanstack/react-router";
import { ArrowLeft, BookOpenCheck, Leaf, Quote, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";
import teaPlant from "@/assets/tea-plant.jpg";

const highlights = [
  { icon: Quote, text: "Câu trả lời kèm nguồn trích dẫn từ tài liệu kỹ thuật" },
  { icon: BookOpenCheck, text: "Lưu và mở lại lịch sử các cuộc trò chuyện" },
  { icon: ShieldCheck, text: "Phiên chat của bạn chỉ bạn truy cập được" },
];

/** Bố cục hai cột toàn màn hình dùng chung cho trang đăng nhập và đăng ký. */
export function AuthLayout({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer: ReactNode;
}) {
  return (
    <div className="grid min-h-svh lg:grid-cols-2">
      <aside className="relative hidden overflow-hidden lg:block">
        <img
          src={teaPlant}
          alt=""
          width={1024}
          height={768}
          className="absolute inset-0 size-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-emerald-950 via-emerald-950/70 to-emerald-950/30" />
        <div className="relative flex h-full flex-col justify-between p-10 text-white xl:p-14">
          <div className="flex items-center gap-3">
            <div className="grid size-11 place-items-center rounded-xl bg-amber text-amber-foreground shadow-soft">
              <Leaf className="size-5" />
            </div>
            <div>
              <p className="font-display text-xl font-semibold leading-tight">Tea Scholar</p>
              <p className="text-xs text-white/70">Trợ lý tri thức cây chè Việt Nam</p>
            </div>
          </div>
          <div>
            <h2 className="max-w-md font-display text-4xl font-semibold leading-tight">
              Tri thức cây chè, có nguồn để kiểm chứng
            </h2>
            <ul className="mt-8 space-y-4">
              {highlights.map((item) => (
                <li key={item.text} className="flex items-start gap-3 text-sm text-white/85">
                  <item.icon className="mt-0.5 size-4 shrink-0 text-amber" />
                  {item.text}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </aside>

      <main className="flex flex-col bg-background px-6 py-8 sm:px-12">
        <Link
          to="/"
          className="inline-flex w-fit items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="size-4" />
          Về trang chủ
        </Link>
        <div className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center py-10">
          <div className="grid size-12 place-items-center rounded-2xl bg-primary text-primary-foreground shadow-soft lg:hidden">
            <Leaf className="size-6" />
          </div>
          <h1 className="mt-6 text-3xl font-semibold lg:mt-0">{title}</h1>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">{subtitle}</p>
          <div className="mt-8">{children}</div>
          <div className="mt-6 text-center text-sm text-muted-foreground">{footer}</div>
        </div>
      </main>
    </div>
  );
}
