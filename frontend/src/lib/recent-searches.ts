const STORAGE_KEY = "tea_scholar_recent_searches";
const MAX_ITEMS = 8;

function readAll(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((x): x is string => typeof x === "string") : [];
  } catch {
    return []; // localStorage bị chặn (chế độ riêng tư) hoặc dữ liệu hỏng
  }
}

function writeAll(items: string[]): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  } catch {
    // Không lưu được thì bỏ qua: lịch sử chỉ là tiện ích, không ảnh hưởng chức năng chính
  }
}

/** Lịch sử tìm kiếm gần nhất (mới nhất trước), lưu trên trình duyệt của người dùng. */
export function getRecentSearches(): string[] {
  return readAll();
}

export function addRecentSearch(term: string): string[] {
  const clean = term.trim();
  if (!clean) return readAll();
  const next = [clean, ...readAll().filter((x) => x.toLowerCase() !== clean.toLowerCase())].slice(
    0,
    MAX_ITEMS,
  );
  writeAll(next);
  return next;
}

export function removeRecentSearch(term: string): string[] {
  const next = readAll().filter((x) => x !== term);
  writeAll(next);
  return next;
}
