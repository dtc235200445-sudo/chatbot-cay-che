import { createFileRoute, Link } from "@tanstack/react-router";
import {
  AlertCircle,
  ArrowRight,
  BookText,
  CalendarDays,
  ChevronDown,
  FileText,
  Loader2,
  MessageCircleQuestion,
  Search as SearchIcon,
} from "lucide-react";
import { Fragment, useCallback, useEffect, useRef, useState } from "react";
import { z } from "zod";
import { EmptyState, PageHeader } from "@/components/common/page-elements";
import { SearchSuggestBox } from "@/components/common/search-suggest-box";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { apiClient } from "@/lib/api-client";
import { addRecentSearch } from "@/lib/recent-searches";
import type { KnowledgeChunkResponse } from "@/types/api";

const PAGE_SIZE = 12;
const SUGGESTED_KEYWORDS = ["thối búp", "bọ trĩ", "nhện đỏ", "đốn chè", "bón phân", "chế biến"];

export const Route = createFileRoute("/search")({
  validateSearch: (search) => z.object({ q: z.string().optional() }).parse(search),
  head: () => ({
    meta: [
      { title: "Tìm kiếm tri thức — Tea Scholar" },
      {
        name: "description",
        content: "Tra cứu nguyên văn các đoạn tài liệu kỹ thuật về cây chè Việt Nam.",
      },
      { property: "og:title", content: "Tìm kiếm tri thức — Tea Scholar" },
      {
        property: "og:description",
        content: "Tra cứu tài liệu kỹ thuật trồng, chăm sóc và phòng trừ sâu bệnh cho chè.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: SearchPage,
});

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Tô sáng các từ khóa người dùng đã nhập trong đoạn văn bản. */
function Highlight({ text, query }: { text: string; query: string }) {
  // Backend tìm theo cụm ký tự người dùng nhập, nên tô nguyên cụm (không tô từng từ rời)
  const phrase = query.trim();
  const terms = phrase.length > 1 ? [phrase] : [];
  if (terms.length === 0) return <>{text}</>;
  const pattern = new RegExp(`(${terms.map(escapeRegExp).join("|")})`, "gi");
  return (
    <>
      {text.split(pattern).map((part, index) =>
        // Các phần ở vị trí lẻ là phần khớp với nhóm bắt trong biểu thức chính quy
        index % 2 === 1 ? (
          <mark key={index} className="rounded bg-amber/40 px-0.5 text-foreground">
            {part}
          </mark>
        ) : (
          <Fragment key={index}>{part}</Fragment>
        ),
      )}
    </>
  );
}

function ResultCard({ chunk, query }: { chunk: KnowledgeChunkResponse; query: string }) {
  const [expanded, setExpanded] = useState(false);
  const isLong = chunk.content.length > 320;

  return (
    <article className="rounded-2xl border bg-card p-5 shadow-soft transition-shadow hover:shadow-lift sm:p-6">
      <div className="flex items-start gap-4">
        <div className="mt-0.5 hidden size-10 shrink-0 place-items-center rounded-xl bg-tea-soft text-primary sm:grid">
          <FileText className="size-5" />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="text-lg font-semibold leading-snug">
            <Highlight text={chunk.title} query={query} />
          </h3>
          <p
            className={`mt-3 whitespace-pre-line text-sm leading-7 text-foreground/80 ${expanded ? "" : "line-clamp-4"}`}
          >
            <Highlight text={chunk.content} query={query} />
          </p>
          {isLong && (
            <button
              type="button"
              onClick={() => setExpanded((v) => !v)}
              className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
            >
              {expanded ? "Thu gọn" : "Đọc tiếp"}
              <ChevronDown
                className={`size-4 transition-transform ${expanded ? "rotate-180" : ""}`}
              />
            </button>
          )}
          <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 border-t pt-4 text-xs text-muted-foreground">
            <span className="flex min-w-0 items-center gap-1.5">
              <BookText className="size-3.5 shrink-0" />
              <span className="truncate" title={chunk.source}>
                {chunk.source}
                {chunk.page ? `, trang ${chunk.page}` : ""}
              </span>
            </span>
            {chunk.year && (
              <span className="flex items-center gap-1.5">
                <CalendarDays className="size-3.5" />
                {chunk.year}
              </span>
            )}
            <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px]">
              {chunk.chunk_id}
            </code>
            <Link
              to="/assistant"
              search={{ q: chunk.title }}
              className="ml-auto inline-flex items-center gap-1 font-medium text-primary hover:underline"
            >
              <MessageCircleQuestion className="size-3.5" />
              Hỏi trợ lý
              <ArrowRight className="size-3.5" />
            </Link>
          </div>
        </div>
      </div>
    </article>
  );
}

function SearchPage() {
  const { q } = Route.useSearch();
  const [query, setQuery] = useState(q ?? "");
  const [activeQuery, setActiveQuery] = useState("");
  const [results, setResults] = useState<KnowledgeChunkResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const requestId = useRef(0);

  const runSearch = useCallback(async (term: string, nextPage: number) => {
    const id = ++requestId.current;
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.knowledge.search(term, nextPage, PAGE_SIZE);
      if (id !== requestId.current) return; // đã có yêu cầu mới hơn
      setResults((prev) => (nextPage === 1 ? response.items : [...prev, ...response.items]));
      setTotal(response.total);
      setPage(nextPage);
      setActiveQuery(term);
      setHasSearched(true);
    } catch (err: unknown) {
      if (id !== requestId.current) return;
      setError(err instanceof Error ? err.message : "Đã có lỗi xảy ra khi tra cứu.");
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, []);

  // Tự tra cứu khi vào trang bằng đường dẫn có ?q=
  useEffect(() => {
    const initial = q?.trim();
    if (initial) {
      setQuery(initial);
      void runSearch(initial, 1);
    }
  }, [q, runSearch]);

  const searchKeyword = (keyword: string) => {
    setQuery(keyword);
    addRecentSearch(keyword);
    void runSearch(keyword, 1);
  };

  const hasMore = results.length < total;

  return (
    <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6 lg:px-10 lg:py-14">
      <PageHeader
        eyebrow="Cơ sở tri thức"
        title="Tìm kiếm tri thức"
        subtitle="Tra cứu nguyên văn các đoạn tài liệu kỹ thuật về chè. Muốn có câu trả lời tổng hợp, hãy hỏi trợ lý AI."
      />

      <SearchSuggestBox
        value={query}
        onChange={setQuery}
        onSearch={(term) => void runSearch(term, 1)}
        loading={loading && page === 1}
        placeholder="Nhập từ khóa, ví dụ: bọ trĩ, thối búp, đốn chè…"
      />

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <span className="text-xs text-muted-foreground">Gợi ý:</span>
        {SUGGESTED_KEYWORDS.map((keyword) => (
          <button
            key={keyword}
            type="button"
            onClick={() => searchKeyword(keyword)}
            className="rounded-full border bg-card px-3 py-1 text-sm text-foreground/80 transition-colors hover:border-primary/40 hover:bg-tea-soft hover:text-primary"
          >
            {keyword}
          </button>
        ))}
      </div>

      {error && (
        <Alert variant="destructive" className="mt-6">
          <AlertCircle className="size-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="mt-10">
        {hasSearched && (
          <div className="mb-5 flex items-baseline justify-between gap-3">
            <h2 className="font-display text-lg font-semibold">
              {total > 0 ? `${total} kết quả cho “${activeQuery}”` : `Kết quả cho “${activeQuery}”`}
            </h2>
            {total > 0 && (
              <span className="text-xs text-muted-foreground">
                Hiển thị {results.length}/{total}
              </span>
            )}
          </div>
        )}

        {loading && page === 1 ? (
          <div className="space-y-4">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-44 rounded-2xl" />
            ))}
          </div>
        ) : results.length > 0 ? (
          <>
            <div className="space-y-4">
              {results.map((chunk) => (
                <ResultCard key={chunk.chunk_id} chunk={chunk} query={activeQuery} />
              ))}
            </div>
            {hasMore && (
              <div className="mt-6 text-center">
                <Button
                  variant="outline"
                  className="rounded-full"
                  disabled={loading}
                  onClick={() => void runSearch(activeQuery, page + 1)}
                >
                  {loading ? <Loader2 className="animate-spin" /> : null}
                  Xem thêm kết quả
                </Button>
              </div>
            )}
          </>
        ) : hasSearched && !error ? (
          <EmptyState
            title="Không tìm thấy kết quả"
            description="Thử từ khóa ngắn hơn hoặc dùng thuật ngữ khác. Bạn cũng có thể hỏi trực tiếp trợ lý AI."
          >
            <Button asChild variant="outline" className="rounded-full">
              <Link to="/assistant" search={{ q: activeQuery }}>
                Hỏi trợ lý về “{activeQuery}”
                <ArrowRight />
              </Link>
            </Button>
          </EmptyState>
        ) : !error ? (
          <EmptyState
            icon={SearchIcon}
            title="Bắt đầu tra cứu"
            description="Nhập từ khóa hoặc chọn một gợi ý phía trên để xem các đoạn tài liệu liên quan."
          />
        ) : null}
      </div>
    </div>
  );
}
