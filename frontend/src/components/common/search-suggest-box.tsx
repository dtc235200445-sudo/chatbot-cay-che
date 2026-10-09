import { Clock, Loader2, Search as SearchIcon, X } from "lucide-react";
import {
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api-client";
import { addRecentSearch, getRecentSearches, removeRecentSearch } from "@/lib/recent-searches";
import { cn } from "@/lib/utils";

const DEBOUNCE_MS = 120;
const MAX_ITEMS = 8;
const MAX_HISTORY_SHOWN = 4;

interface Item {
  text: string;
  kind: "history" | "suggestion";
}

/** Phần người dùng đã gõ hiển thị thường, phần gợi ý còn lại in đậm (giống thanh địa chỉ trình duyệt). */
function TypedAndRest({ text, typed }: { text: string; typed: string }) {
  const clean = typed.trimStart();
  if (clean && text.toLowerCase().startsWith(clean.toLowerCase())) {
    return (
      <>
        <span>{text.slice(0, clean.length)}</span>
        <strong className="font-semibold">{text.slice(clean.length)}</strong>
      </>
    );
  }
  return <span>{text}</span>;
}

export function SearchSuggestBox({
  value,
  onChange,
  onSearch,
  loading = false,
  placeholder,
}: {
  value: string;
  onChange: (value: string) => void;
  /** Được gọi khi người dùng gửi từ khóa (Enter, bấm Tìm hoặc chọn một gợi ý). */
  onSearch: (term: string) => void;
  loading?: boolean;
  placeholder?: string;
}) {
  const listId = useId();
  const containerRef = useRef<HTMLDivElement>(null);
  const requestId = useRef(0);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [history, setHistory] = useState<string[]>([]);

  // Gợi ý từ API, chống trễ: chỉ nhận kết quả của lần gõ mới nhất
  useEffect(() => {
    const term = value.trimStart();
    if (!term.trim()) {
      setSuggestions([]);
      return;
    }
    const id = ++requestId.current;
    const timer = setTimeout(() => {
      apiClient.knowledge
        .suggest(term, MAX_ITEMS)
        .then((list) => {
          if (id === requestId.current) setSuggestions(list);
        })
        .catch(() => {
          if (id === requestId.current) setSuggestions([]); // lỗi gợi ý không được làm hỏng ô tìm kiếm
        });
    }, DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [value]);

  const items = useMemo<Item[]>(() => {
    const typed = value.trimStart().toLowerCase();
    const historyMatches = history
      .filter((h) => !typed || (h.toLowerCase().startsWith(typed) && h.toLowerCase() !== typed))
      .slice(0, MAX_HISTORY_SHOWN)
      .map<Item>((text) => ({ text, kind: "history" }));
    const taken = new Set(historyMatches.map((h) => h.text.toLowerCase()));
    const rest = suggestions
      .filter((s) => !taken.has(s.toLowerCase()))
      .map<Item>((text) => ({ text, kind: "suggestion" }));
    return [...historyMatches, ...rest].slice(0, MAX_ITEMS);
  }, [history, suggestions, value]);

  useEffect(() => {
    setActive(-1);
  }, [items]);

  // Đóng danh sách khi bấm ra ngoài
  useEffect(() => {
    const onPointerDown = (event: PointerEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, []);

  const submit = useCallback(
    (term: string) => {
      const clean = term.trim();
      if (!clean) return;
      onChange(clean);
      setHistory(addRecentSearch(clean));
      setOpen(false);
      setActive(-1);
      onSearch(clean);
    },
    [onChange, onSearch],
  );

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      if (items.length === 0) return;
      event.preventDefault();
      setOpen(true);
      const step = event.key === "ArrowDown" ? 1 : -1;
      setActive((prev) => {
        const next = prev + step;
        if (next < -1) return items.length - 1;
        if (next >= items.length) return -1;
        return next;
      });
    } else if (event.key === "Enter") {
      // Bỏ qua khi bộ gõ tiếng Việt (Telex/VNI) đang soạn chữ: Enter lúc đó là để chốt chữ, không phải gửi
      if (event.nativeEvent.isComposing) return;
      event.preventDefault();
      const chosen = active >= 0 ? items[active] : undefined;
      submit(chosen ? chosen.text : value);
    } else if (event.key === "Escape") {
      setOpen(false);
      setActive(-1);
    }
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    const chosen = active >= 0 ? items[active] : undefined;
    submit(chosen ? chosen.text : value);
  };

  const showList = open && items.length > 0;

  return (
    <div ref={containerRef} className="relative">
      <form onSubmit={handleSubmit} role="search" className="relative">
        <SearchIcon className="pointer-events-none absolute left-5 top-1/2 size-5 -translate-y-1/2 text-muted-foreground" />
        <input
          value={value}
          onChange={(event) => {
            onChange(event.target.value);
            setOpen(true);
          }}
          onFocus={() => {
            setHistory(getRecentSearches());
            setOpen(true);
          }}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          autoComplete="off"
          spellCheck={false}
          role="combobox"
          aria-label="Từ khóa tra cứu"
          aria-expanded={showList}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={active >= 0 ? `${listId}-${active}` : undefined}
          className={cn(
            "h-16 w-full border bg-card pl-14 pr-36 text-base shadow-soft outline-none transition-shadow placeholder:text-muted-foreground focus:border-primary focus:shadow-lift",
            showList ? "rounded-t-2xl rounded-b-none border-b-transparent" : "rounded-2xl",
          )}
        />
        {value && (
          <button
            type="button"
            onClick={() => {
              onChange("");
              setOpen(true);
            }}
            className="absolute right-24 top-1/2 grid size-8 -translate-y-1/2 place-items-center rounded-full text-muted-foreground hover:bg-muted hover:text-foreground"
            aria-label="Xóa từ khóa"
          >
            <X className="size-4" />
          </button>
        )}
        <Button
          type="submit"
          disabled={!value.trim() || loading}
          className="absolute right-2.5 top-1/2 h-11 -translate-y-1/2 rounded-xl px-5"
        >
          {loading ? <Loader2 className="animate-spin" /> : null}
          Tìm
        </Button>
      </form>

      {showList && (
        <ul
          id={listId}
          role="listbox"
          className="absolute inset-x-0 top-full z-30 overflow-hidden rounded-b-2xl border border-t-0 border-primary bg-card py-1 shadow-lift"
        >
          {items.map((item, index) => (
            <li
              key={`${item.kind}-${item.text}`}
              id={`${listId}-${index}`}
              role="option"
              aria-selected={index === active}
              onMouseEnter={() => setActive(index)}
              // mousedown (không phải click) để chọn trước khi ô nhập mất focus
              onMouseDown={(event) => {
                event.preventDefault();
                submit(item.text);
              }}
              className={cn(
                "flex cursor-pointer items-center gap-3 px-5 py-2.5 text-[15px]",
                index === active ? "bg-tea-soft" : "hover:bg-muted",
              )}
            >
              {item.kind === "history" ? (
                <Clock className="size-4 shrink-0 text-muted-foreground" />
              ) : (
                <SearchIcon className="size-4 shrink-0 text-muted-foreground" />
              )}
              <span className="min-w-0 flex-1 truncate">
                <TypedAndRest text={item.text} typed={value} />
              </span>
              {item.kind === "history" && (
                <button
                  type="button"
                  aria-label={`Xóa “${item.text}” khỏi lịch sử tìm kiếm`}
                  onMouseDown={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    setHistory(removeRecentSearch(item.text));
                  }}
                  className="grid size-7 shrink-0 place-items-center rounded-full text-muted-foreground hover:bg-background hover:text-foreground"
                >
                  <X className="size-4" />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
