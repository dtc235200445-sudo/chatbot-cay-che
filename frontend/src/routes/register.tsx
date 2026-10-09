import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, type FormEvent } from "react";
import { AlertCircle, Loader2, UserPlus } from "lucide-react";
import { AuthLayout } from "@/components/layout/auth-layout";
import { useAuth } from "@/context/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";

export const Route = createFileRoute("/register")({
  head: () => ({
    meta: [
      { title: "Đăng ký — Tea Scholar" },
      {
        name: "description",
        content: "Tạo tài khoản để lưu lịch sử trò chuyện với trợ lý cây chè.",
      },
    ],
  }),
  component: RegisterPage,
});

function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !email.trim() || !password) return;

    setError(null);
    setSubmitting(true);
    try {
      await register({
        username: username.trim(),
        email: email.trim(),
        password,
        full_name: fullName.trim() || undefined,
      });
      void navigate({ to: "/assistant" });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Đăng ký thất bại. Vui lòng thử lại.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Tạo tài khoản"
      subtitle="Tài khoản giúp bạn lưu lại các cuộc trò chuyện với trợ lý."
      footer={
        <>
          Đã có tài khoản?{" "}
          <Link to="/login" className="font-medium text-primary hover:underline">
            Đăng nhập
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
      <form className="space-y-4" onSubmit={handleSubmit}>
        <div className="space-y-2">
          <Label htmlFor="username">Tên đăng nhập</Label>
          <Input
            id="username"
            type="text"
            autoComplete="username"
            required
            minLength={3}
            maxLength={50}
            className="h-12 rounded-xl"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Ít nhất 3 ký tự"
            disabled={submitting}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            required
            className="h-12 rounded-xl"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="ten@example.com"
            disabled={submitting}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="fullName">
            Họ và tên <span className="font-normal text-muted-foreground">(không bắt buộc)</span>
          </Label>
          <Input
            id="fullName"
            type="text"
            autoComplete="name"
            className="h-12 rounded-xl"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Nguyễn Văn A"
            disabled={submitting}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="password">Mật khẩu</Label>
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            required
            minLength={6}
            className="h-12 rounded-xl"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Ít nhất 6 ký tự"
            disabled={submitting}
          />
        </div>
        <Button
          type="submit"
          className="mt-2 h-12 w-full rounded-xl"
          size="lg"
          disabled={submitting}
        >
          {submitting ? <Loader2 className="animate-spin" /> : <UserPlus />}
          {submitting ? "Đang tạo tài khoản…" : "Tạo tài khoản"}
        </Button>
      </form>
    </AuthLayout>
  );
}
