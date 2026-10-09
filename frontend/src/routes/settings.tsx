import { createFileRoute } from "@tanstack/react-router";
import { Check, FileText, Globe2, Monitor, SlidersHorizontal, Sparkles } from "lucide-react";
import { useState } from "react";
import { PageHeader } from "@/components/common/page-elements";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "Cài đặt — Tea AI" },
      {
        name: "description",
        content: "Tùy chỉnh giao diện nghiên cứu và cấu hình phản hồi Trợ lý Tea AI.",
      },
      { property: "og:title", content: "Cài đặt — Tea AI" },
      { property: "og:description", content: "Cấu hình giao diện Tea AI." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: SettingsPage,
});

function SettingRow({
  icon: Icon,
  title,
  description,
  children,
}: {
  icon: typeof Monitor;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col justify-between gap-4 border-b py-6 last:border-b-0 sm:flex-row sm:items-center">
      <div className="flex gap-3">
        <div className="grid size-9 shrink-0 place-items-center rounded-md bg-secondary text-secondary-foreground">
          <Icon className="size-4" />
        </div>
        <div>
          <h3 className="text-sm font-medium">{title}</h3>
          <p className="mt-1 text-xs text-muted-foreground">{description}</p>
        </div>
      </div>
      <div className="shrink-0 sm:min-w-52">{children}</div>
    </div>
  );
}

function SettingsPage() {
  const [detail, setDetail] = useState("cân bằng");
  const [sources, setSources] = useState(true);
  const [animations, setAnimations] = useState(true);
  const [saved, setSaved] = useState(false);
  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-10 lg:py-10">
      <PageHeader
        title="Cài đặt Hệ thống"
        subtitle="Tùy chỉnh giao diện hiển thị và tùy chọn phản hồi của Trợ lý Tea AI."
      />
      <section className="border bg-card px-5 sm:px-6">
        <h2 className="border-b py-5 text-sm font-semibold">Cấu hình Chung</h2>
        <SettingRow icon={Monitor} title="Giao diện" description="Chế độ màu hiển thị">
          <Select defaultValue="light">
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="light">Chế độ sáng</SelectItem>
            </SelectContent>
          </Select>
        </SettingRow>
        <SettingRow icon={Globe2} title="Ngôn ngữ" description="Ngôn ngữ giao diện ưu tiên">
          <Select defaultValue="vietnamese">
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="vietnamese">Tiếng Việt</SelectItem>
              <SelectItem value="english">Tiếng Anh</SelectItem>
            </SelectContent>
          </Select>
        </SettingRow>
      </section>
      <section className="mt-6 border bg-card px-5 sm:px-6">
        <h2 className="border-b py-5 text-sm font-semibold">Cấu hình Phản hồi AI</h2>
        <SettingRow
          icon={SlidersHorizontal}
          title="Mức độ chi tiết"
          description="Độ dài câu trả lời của Trợ lý AI"
        >
          <div className="grid grid-cols-3 gap-1 rounded-md bg-muted p-1">
            {[
              { label: "Ngắn gọn", val: "ngắn gọn" },
              { label: "Cân bằng", val: "cân bằng" },
              { label: "Chi tiết", val: "chi tiết" },
            ].map((item) => (
              <Button
                key={item.val}
                variant={detail === item.val ? "default" : "ghost"}
                size="sm"
                className="px-2"
                onClick={() => setDetail(item.val)}
              >
                {item.label}
              </Button>
            ))}
          </div>
        </SettingRow>
      </section>
      <section className="mt-6 border bg-card px-5 sm:px-6">
        <h2 className="border-b py-5 text-sm font-semibold">Giao diện Người dùng</h2>
        <SettingRow
          icon={FileText}
          title="Hiển thị trích dẫn nguồn"
          description="Đính kèm tài liệu tham khảo trong câu trả lời AI"
        >
          <div className="flex justify-end">
            <Switch
              checked={sources}
              onCheckedChange={setSources}
              aria-label="Hiển thị trích dẫn nguồn"
            />
          </div>
        </SettingRow>
        <SettingRow
          icon={Sparkles}
          title="Hiệu ứng chuyển động"
          description="Sử dụng hiệu ứng chuyển trang mượt mà"
        >
          <div className="flex justify-end">
            <Switch
              checked={animations}
              onCheckedChange={setAnimations}
              aria-label="Hiệu ứng chuyển động"
            />
          </div>
        </SettingRow>
      </section>
      <div className="mt-6 flex items-center justify-end gap-3">
        {saved && (
          <span className="flex items-center gap-1 text-xs text-primary">
            <Check className="size-3" />
            Đã lưu tùy chọn cài đặt
          </span>
        )}
        <Button onClick={() => setSaved(true)}>Lưu cài đặt</Button>
      </div>
      <p className="mt-3 text-right text-xs text-muted-foreground">
        Các tùy chọn trên màn hình dùng cho việc thử nghiệm giao diện.
      </p>
    </div>
  );
}
