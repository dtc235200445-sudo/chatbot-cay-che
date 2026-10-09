import { createFileRoute, Link } from "@tanstack/react-router";
import {
  AlertCircle,
  BookOpen,
  Bug,
  Camera,
  CloudSun,
  History,
  Leaf,
  Loader2,
  MessageSquarePlus,
  Scissors,
  Sparkles,
  Trash2,
  Upload,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { z } from "zod";
import {
  Conversation,
  ConversationContent,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation";
import { Message, MessageContent, MessageResponse } from "@/components/ai-elements/message";
import {
  PromptInput,
  PromptInputButton,
  PromptInputFooter,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputTools,
} from "@/components/ai-elements/prompt-input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { useAuth } from "@/context/auth-context";
import { apiClient } from "@/lib/api-client";
import type { ChatSessionResponse, ChatSourceItem } from "@/types/api";

const suggestions: { icon: LucideIcon; title: string; question: string }[] = [
  { icon: Bug, title: "Sâu bệnh hại", question: "Bệnh thối búp trên cây chè có triệu chứng gì?" },
  { icon: CloudSun, title: "Thời tiết", question: "Thời tiết Thái Nguyên hôm nay thế nào?" },
  {
    icon: Sparkles,
    title: "Kết hợp thời tiết và bệnh hại",
    question: "Thời tiết Thái Nguyên hiện tại có điều kiện thuận lợi cho bệnh thối búp không?",
  },
  {
    icon: Scissors,
    title: "Kỹ thuật đốn hái",
    question: "Đốn chè kinh doanh thực hiện như thế nào?",
  },
];

type ChatMessageItem = {
  id: string | number;
  role: "user" | "assistant";
  text: string;
  sources?: ChatSourceItem[];
};

export const Route = createFileRoute("/assistant")({
  validateSearch: (search) => z.object({ q: z.string().optional() }).parse(search),
  head: () => ({
    meta: [
      { title: "Trợ lý AI — Tea Scholar" },
      {
        name: "description",
        content:
          "Đặt câu hỏi về kỹ thuật canh tác, sâu bệnh hại và thời tiết vùng chè. Câu trả lời kèm nguồn trích dẫn.",
      },
      { property: "og:title", content: "Trợ lý AI — Tea Scholar" },
      { property: "og:description", content: "Trợ lý tri thức cây chè Việt Nam." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: AssistantPage,
});

function parseSources(raw?: string | null): ChatSourceItem[] {
  if (!raw) return [];
  try {
    const data: unknown = JSON.parse(raw);
    return Array.isArray(data) ? (data as ChatSourceItem[]) : [];
  } catch {
    return [];
  }
}

function AssistantAvatar() {
  return (
    <div className="grid size-9 shrink-0 place-items-center rounded-full bg-primary text-primary-foreground shadow-soft">
      <Leaf className="size-4" />
    </div>
  );
}

function SourceList({ sources }: { sources: ChatSourceItem[] }) {
  return (
    <div className="mt-5 border-t pt-4">
      <p className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        <BookOpen className="size-3.5" />
        Nguồn tham khảo ({sources.length})
      </p>
      <ul className="grid gap-2 sm:grid-cols-2">
        {sources.map((src) => {
          const percent = Math.round(src.similarity_score * 100);
          return (
            <li key={src.chunk_id}>
              <Link
                to="/search"
                search={{ q: src.title }}
                className="block rounded-xl border bg-background p-3 transition-colors hover:border-primary/40 hover:bg-tea-soft/50"
              >
                <p className="line-clamp-2 text-sm font-medium leading-snug" title={src.title}>
                  {src.title}
                </p>
                <p className="mt-1 truncate text-xs text-muted-foreground" title={src.source}>
                  {src.source}
                </p>
                <div className="mt-2.5 flex items-center gap-2">
                  <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full rounded-full bg-primary"
                      style={{ width: `${percent}%` }}
                    />
                  </div>
                  <span className="text-[11px] tabular-nums text-muted-foreground">{percent}%</span>
                </div>
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function HistoryPanel({
  open,
  onOpenChange,
  activeId,
  onSelect,
  onDeleted,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  activeId: number | null;
  onSelect: (session: ChatSessionResponse) => void;
  onDeleted: (id: number) => void;
}) {
  const [sessions, setSessions] = useState<ChatSessionResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setError(null);
    apiClient.chat
      .getSessions()
      .then((data) => {
        if (!cancelled) setSessions(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Không tải được lịch sử.");
      });
    return () => {
      cancelled = true;
    };
  }, [open]);

  const openSession = async (id: number) => {
    setBusyId(id);
    try {
      onSelect(await apiClient.chat.getSession(id));
      onOpenChange(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Không mở được cuộc trò chuyện.");
    } finally {
      setBusyId(null);
    }
  };

  const removeSession = async (id: number) => {
    setBusyId(id);
    try {
      await apiClient.chat.deleteSession(id);
      setSessions((prev) => prev?.filter((s) => s.id !== id) ?? null);
      onDeleted(id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Không xóa được cuộc trò chuyện.");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="flex flex-col gap-0 p-0">
        <SheetHeader className="border-b p-5 text-left">
          <SheetTitle className="font-display">Lịch sử trò chuyện</SheetTitle>
          <SheetDescription>Các cuộc trò chuyện đã lưu trong tài khoản của bạn.</SheetDescription>
        </SheetHeader>
        <div className="flex-1 overflow-y-auto p-3">
          {error && (
            <Alert variant="destructive" className="mb-3">
              <AlertCircle className="size-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          {sessions === null && !error ? (
            <div className="grid place-items-center py-12 text-muted-foreground">
              <Loader2 className="size-5 animate-spin" />
            </div>
          ) : sessions && sessions.length === 0 ? (
            <p className="px-3 py-12 text-center text-sm text-muted-foreground">
              Chưa có cuộc trò chuyện nào. Hãy đặt câu hỏi đầu tiên.
            </p>
          ) : (
            <ul className="space-y-1">
              {sessions?.map((session) => (
                <li
                  key={session.id}
                  className={`group flex items-center gap-1 rounded-xl ${
                    session.id === activeId ? "bg-tea-soft" : "hover:bg-muted"
                  }`}
                >
                  <button
                    type="button"
                    disabled={busyId === session.id}
                    onClick={() => void openSession(session.id)}
                    className="min-w-0 flex-1 px-3 py-2.5 text-left"
                  >
                    <p className="truncate text-sm font-medium">{session.title}</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {new Date(session.updated_at).toLocaleString("vi-VN", {
                        day: "2-digit",
                        month: "2-digit",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </p>
                  </button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="mr-1 size-8 shrink-0 text-muted-foreground opacity-0 hover:text-destructive focus-visible:opacity-100 group-hover:opacity-100"
                    disabled={busyId === session.id}
                    onClick={() => void removeSession(session.id)}
                    title="Xóa cuộc trò chuyện"
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}

function AssistantPage() {
  const { q } = Route.useSearch();
  const { user } = useAuth();
  const [input, setInput] = useState(q ?? "");
  const [messages, setMessages] = useState<ChatMessageItem[]>([]);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastQuestion, setLastQuestion] = useState<string | null>(null);
  const [imageModalOpen, setImageModalOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const busyRef = useRef(false);

  const sendQuery = useCallback(
    async (text: string) => {
      const cleanMsg = text.trim();
      if (!cleanMsg || busyRef.current) return;

      busyRef.current = true;
      setError(null);
      setInput("");
      setLastQuestion(cleanMsg);
      setMessages((prev) => [...prev, { id: `u-${Date.now()}`, role: "user", text: cleanMsg }]);
      setLoading(true);

      try {
        const response = await apiClient.chat.query({ message: cleanMsg, session_id: sessionId });
        if (response.session_id) setSessionId(response.session_id);
        setMessages((prev) => [
          ...prev,
          {
            id: response.message_id || `a-${Date.now()}`,
            role: "assistant",
            text: response.answer,
            sources: response.sources || [],
          },
        ]);
        setLastQuestion(null);
      } catch (err: unknown) {
        setError(
          err instanceof Error ? err.message : "Đã có lỗi xảy ra khi kết nối tới trợ lý AI.",
        );
      } finally {
        busyRef.current = false;
        setLoading(false);
      }
    },
    [sessionId],
  );

  // Gửi câu hỏi từ ?q= đúng một lần (ref chặn effect chạy hai lần ở StrictMode)
  const autoSentQuery = useRef<string | null>(null);
  useEffect(() => {
    const initial = q?.trim();
    if (initial && autoSentQuery.current !== initial) {
      autoSentQuery.current = initial;
      void sendQuery(initial);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- chỉ gửi lại khi tham số ?q= đổi
  }, [q]);

  const startNewChat = () => {
    setMessages([]);
    setSessionId(null);
    setError(null);
    setLastQuestion(null);
    setInput("");
  };

  const loadSession = (session: ChatSessionResponse) => {
    const restored = [...(session.messages ?? [])]
      .sort((a, b) => a.id - b.id)
      .filter((m) => m.role === "user" || m.role === "assistant")
      .map<ChatMessageItem>((m) => ({
        id: m.id,
        role: m.role as "user" | "assistant",
        text: m.content,
        sources: m.role === "assistant" ? parseSources(m.sources_json) : [],
      }));
    setMessages(restored);
    setSessionId(session.id);
    setError(null);
    setLastQuestion(null);
  };

  const isEmpty = messages.length === 0 && !loading;

  return (
    <div className="flex h-[calc(100svh-64px)] min-h-[520px] flex-col">
      <div className="flex items-center justify-between gap-3 border-b bg-background/60 px-4 py-3 sm:px-6">
        <div className="min-w-0">
          <h1 className="truncate font-display text-lg font-semibold">Trợ lý AI cây chè</h1>
          <p className="truncate text-xs text-muted-foreground">
            {sessionId ? `Cuộc trò chuyện #${sessionId}` : "Cuộc trò chuyện mới"}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {user && (
            <Button
              variant="outline"
              size="sm"
              className="rounded-full"
              onClick={() => setHistoryOpen(true)}
            >
              <History />
              <span className="hidden sm:inline">Lịch sử</span>
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            className="rounded-full"
            onClick={startNewChat}
            disabled={isEmpty || loading}
          >
            <MessageSquarePlus />
            <span className="hidden sm:inline">Cuộc trò chuyện mới</span>
          </Button>
        </div>
      </div>

      <Conversation className="min-h-0 flex-1">
        <ConversationContent className="mx-auto w-full max-w-3xl gap-7 px-4 py-8 sm:px-6">
          {isEmpty ? (
            <div className="py-6 text-center sm:py-12">
              <div className="mx-auto grid size-16 place-items-center rounded-2xl bg-primary text-primary-foreground shadow-lift">
                <Leaf className="size-8" />
              </div>
              <h2 className="mt-6 font-display text-3xl font-semibold">
                Bạn muốn hỏi gì về cây chè?
              </h2>
              <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-muted-foreground">
                Trợ lý trả lời dựa trên tài liệu kỹ thuật và thời tiết trực tiếp, kèm nguồn để bạn
                kiểm chứng.
              </p>
              <div className="mt-8 grid gap-3 text-left sm:grid-cols-2">
                {suggestions.map((item) => (
                  <button
                    key={item.question}
                    type="button"
                    onClick={() => void sendQuery(item.question)}
                    className="group flex items-start gap-3 rounded-2xl border bg-card p-4 shadow-soft transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-lift"
                  >
                    <div className="grid size-9 shrink-0 place-items-center rounded-lg bg-tea-soft text-primary">
                      <item.icon className="size-4" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs font-semibold uppercase tracking-wider text-primary">
                        {item.title}
                      </p>
                      <p className="mt-1 text-sm leading-5">{item.question}</p>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((message) =>
              message.role === "user" ? (
                <Message key={message.id} from="user" className="max-w-[85%]">
                  <MessageContent className="rounded-2xl rounded-br-md px-4 py-3 text-[15px] leading-6 group-[.is-user]:bg-primary group-[.is-user]:text-primary-foreground">
                    {message.text}
                  </MessageContent>
                </Message>
              ) : (
                <Message key={message.id} from="assistant" className="max-w-full">
                  <div className="flex gap-3">
                    <AssistantAvatar />
                    <MessageContent className="w-full min-w-0 flex-1 rounded-2xl rounded-tl-md border bg-card px-5 py-4 shadow-soft">
                      <MessageResponse>{message.text}</MessageResponse>
                      {message.sources && message.sources.length > 0 && (
                        <SourceList sources={message.sources} />
                      )}
                    </MessageContent>
                  </div>
                </Message>
              ),
            )
          )}

          {loading && (
            <div className="flex items-center gap-3">
              <AssistantAvatar />
              <div className="flex items-center gap-3 rounded-2xl rounded-tl-md border bg-card px-4 py-3 text-sm text-muted-foreground shadow-soft">
                <span className="dot-bounce flex gap-1" aria-hidden>
                  <span className="size-1.5 rounded-full bg-primary" />
                  <span className="size-1.5 rounded-full bg-primary" />
                  <span className="size-1.5 rounded-full bg-primary" />
                </span>
                Đang tra cứu tri thức và tổng hợp câu trả lời…
              </div>
            </div>
          )}

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="size-4" />
              <AlertDescription className="flex flex-wrap items-center justify-between gap-2">
                <span>{error}</span>
                {lastQuestion && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      // Bỏ câu hỏi lỗi vừa thêm rồi gửi lại
                      setMessages((prev) => prev.slice(0, -1));
                      void sendQuery(lastQuestion);
                    }}
                  >
                    Thử lại
                  </Button>
                )}
              </AlertDescription>
            </Alert>
          )}
        </ConversationContent>
        <ConversationScrollButton />
      </Conversation>

      <div className="border-t bg-background px-4 pb-3 pt-3 sm:px-6">
        <PromptInput
          className="mx-auto max-w-3xl rounded-2xl shadow-soft"
          accept="image/*"
          onSubmit={({ text }) => void sendQuery(text)}
        >
          <PromptInputTextarea
            name="message"
            value={input}
            maxLength={2000}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Nhập câu hỏi về cây chè…"
            className="min-h-14"
            disabled={loading}
          />
          <PromptInputFooter>
            <PromptInputTools>
              <PromptInputButton
                tooltip="Chẩn đoán qua ảnh: đang phát triển"
                onClick={() => setImageModalOpen(true)}
              >
                <Camera />
                Chẩn đoán ảnh
              </PromptInputButton>
            </PromptInputTools>
            <PromptInputSubmit
              disabled={!input.trim() || loading}
              status={loading ? "submitted" : "ready"}
            />
          </PromptInputFooter>
        </PromptInput>
        <p className="mx-auto mt-2 max-w-3xl text-center text-[11px] text-muted-foreground">
          Thông tin mang tính tham khảo, dựa trên cơ sở tri thức chè. Không thay thế tư vấn của cán
          bộ kỹ thuật.
        </p>
      </div>

      {user && (
        <HistoryPanel
          open={historyOpen}
          onOpenChange={setHistoryOpen}
          activeId={sessionId}
          onSelect={loadSession}
          onDeleted={(id) => {
            if (id === sessionId) startNewChat();
          }}
        />
      )}

      <Dialog open={imageModalOpen} onOpenChange={setImageModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="font-display">Chẩn đoán qua ảnh lá chè</DialogTitle>
            <DialogDescription>
              Tính năng này chưa được phát hành và nằm trong hướng phát triển tiếp theo.
            </DialogDescription>
          </DialogHeader>
          <div className="grid min-h-44 place-items-center rounded-xl border border-dashed bg-muted/40 p-6 text-center">
            <div>
              <Upload className="mx-auto size-9 text-muted-foreground opacity-60" />
              <p className="mt-4 text-sm font-medium text-muted-foreground">
                Hiện tại hãy mô tả triệu chứng bằng văn bản trong khung chat.
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setImageModalOpen(false)}>
              Đóng
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
