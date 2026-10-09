import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, type FormEvent } from "react";
import { AlertCircle, Loader2, LogIn } from "lucide-react";
import { AuthLayout } from "@/components/layout/auth-layout";
import { useAuth } from "@/context/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [
      { title: "Đăng nhập — Tea Scholar" },
      { name: "description", content: "Đăng nhập để lưu lịch sử trò chuyện với trợ lý cây chè." },
    ],
  }),
  component: LoginPage,
});

function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [usernameOrEmail, setUsernameOrEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!usernameOrEmail.trim() || !password) return;

    setError(null);
    setSubmitting(true);
    try {
      await login({ username_or_email: usernameOrEmail.trim(), password });
      void navigate({ to: "/assistant" });
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Đăng nhập thất bại. Vui lòng kiểm tra lại thông tin.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Đăng nhập"
      subtitle="Đăng nhập để lưu và mở lại các cuộc trò chuyện với trợ lý."
      footer={
        <>
          Chưa có tài khoản?{" "}
          <Link to="/register" className="font-medium text-primary hover:underline">
            Đăng ký ngay
          </Link>
        </>
      }
    >
      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="size-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <form className="space-y-5" onSubmit={handleSubmit}>
        <div className="space-y-2">
          <Label htmlFor="username_or_email">Tên đăng nhập hoặc email</Label>
          <Input
            id="username_or_email"
            type="text"
            autoComplete="username"
            required
            className="h-12 rounded-xl"
            value={usernameOrEmail}
            onChange={(e) => setUsernameOrEmail(e.target.value)}
            placeholder="Nhập tên đăng nhập hoặc email"
            disabled={submitting}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="password">Mật khẩu</Label>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            required
            className="h-12 rounded-xl"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Nhập mật khẩu"
            disabled={submitting}
          />
        </div>
        <Button type="submit" className="h-12 w-full rounded-xl" size="lg" disabled={submitting}>
          {submitting ? <Loader2 className="animate-spin" /> : <LogIn />}
          {submitting ? "Đang đăng nhập…" : "Đăng nhập"}
        </Button>
      </form>
    </AuthLayout>
  );
}
