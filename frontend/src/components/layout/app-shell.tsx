import { Link, useRouterState } from "@tanstack/react-router";
import {
  Bot,
  ChevronsUpDown,
  CloudSun,
  Home,
  LogIn,
  LogOut,
  Search,
  Settings,
  UserPlus,
  WifiOff,
} from "lucide-react";
import type { ReactNode } from "react";
import { TeaBrand } from "@/components/layout/tea-brand";
import { useAuth } from "@/context/auth-context";
import { useApiStatus, type ApiStatus } from "@/hooks/use-api-status";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarRail,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar";
import { cn } from "@/lib/utils";

const mainItems = [
  { title: "Trang chủ", to: "/" as const, icon: Home },
  { title: "Trợ lý AI", to: "/assistant" as const, icon: Bot },
  { title: "Tìm kiếm tri thức", to: "/search" as const, icon: Search },
  { title: "Thời tiết vùng chè", to: "/weather" as const, icon: CloudSun },
];

const PAGE_TITLES: Record<string, string> = {
  "/": "Trang chủ",
  "/assistant": "Trợ lý AI",
  "/search": "Tìm kiếm tri thức",
  "/weather": "Thời tiết vùng chè",
  "/settings": "Cài đặt",
};

const AUTH_PATHS = ["/login", "/register"];

const STATUS_LABEL: Record<ApiStatus, string> = {
  checking: "Đang kiểm tra máy chủ",
  online: "Máy chủ hoạt động",
  offline: "Không kết nối được máy chủ",
};

function StatusPill({ status }: { status: ApiStatus }) {
  return (
    <div
      className="flex shrink-0 items-center gap-2 whitespace-nowrap rounded-full border bg-card px-3 py-1.5 text-xs text-muted-foreground"
      title={STATUS_LABEL[status]}
    >
      <span
        className={cn(
          "size-2 rounded-full",
          status === "online" && "bg-emerald-500",
          status === "offline" && "bg-destructive",
          status === "checking" && "animate-pulse bg-amber",
        )}
      />
      <span className="hidden xl:inline">{STATUS_LABEL[status]}</span>
    </div>
  );
}

function Navigation() {
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const { setOpenMobile } = useSidebar();
  return (
    <>
      <SidebarGroup>
        <SidebarGroupLabel className="text-[11px] uppercase tracking-widest text-sidebar-foreground/50">
          Khám phá
        </SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu className="gap-1">
            {mainItems.map((item) => (
              <SidebarMenuItem key={item.to}>
                <SidebarMenuButton
                  asChild
                  size="lg"
                  isActive={pathname === item.to}
                  tooltip={item.title}
                  className="rounded-xl data-[active=true]:bg-sidebar-primary data-[active=true]:text-sidebar-primary-foreground data-[active=true]:shadow-soft"
                >
                  <Link to={item.to} onClick={() => setOpenMobile(false)}>
                    <item.icon />
                    <span className="font-medium">{item.title}</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
      <SidebarGroup className="mt-2">
        <SidebarGroupLabel className="text-[11px] uppercase tracking-widest text-sidebar-foreground/50">
          Hệ thống
        </SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton
                asChild
                size="lg"
                isActive={pathname === "/settings"}
                tooltip="Cài đặt"
                className="rounded-xl data-[active=true]:bg-sidebar-primary data-[active=true]:text-sidebar-primary-foreground"
              >
                <Link to="/settings" onClick={() => setOpenMobile(false)}>
                  <Settings />
                  <span className="font-medium">Cài đặt</span>
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
    </>
  );
}

function AppSidebar() {
  const { user, logout } = useAuth();

  return (
    <Sidebar collapsible="icon" className="border-sidebar-border">
      <SidebarHeader className="h-[72px] justify-center px-4">
        <TeaBrand />
      </SidebarHeader>
      <SidebarContent className="px-2 py-2">
        <Navigation />
      </SidebarContent>
      <SidebarFooter className="border-t border-sidebar-border p-3">
        {user ? (
          <div className="flex items-center justify-between gap-2 group-data-[collapsible=icon]:justify-center">
            <div className="flex min-w-0 items-center gap-2.5">
              <div className="grid size-9 shrink-0 place-items-center rounded-full bg-sidebar-primary text-xs font-bold uppercase text-sidebar-primary-foreground">
                {user.username.slice(0, 2)}
              </div>
              <div className="min-w-0 group-data-[collapsible=icon]:hidden">
                <p className="truncate text-sm font-medium">{user.full_name || user.username}</p>
                <p className="truncate text-[11px] text-sidebar-foreground/60">{user.email}</p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="size-8 text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground group-data-[collapsible=icon]:hidden"
              onClick={logout}
              title="Đăng xuất"
            >
              <LogOut className="size-4" />
            </Button>
          </div>
        ) : (
          <div className="flex flex-col gap-2 group-data-[collapsible=icon]:hidden">
            <p className="px-1 text-xs leading-5 text-sidebar-foreground/65">
              Đăng nhập để lưu lịch sử hội thoại với trợ lý.
            </p>
            <Button
              asChild
              size="sm"
              className="w-full justify-center gap-2 bg-sidebar-primary text-sidebar-primary-foreground hover:bg-sidebar-primary/90"
            >
              <Link to="/login">
                <LogIn className="size-4" />
                Đăng nhập
              </Link>
            </Button>
            <Button
              asChild
              variant="ghost"
              size="sm"
              className="w-full justify-center gap-2 text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground"
            >
              <Link to="/register">
                <UserPlus className="size-4" />
                Tạo tài khoản
              </Link>
            </Button>
          </div>
        )}
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}

function UserMenu() {
  const { user, logout } = useAuth();

  if (!user) {
    return (
      <div className="flex items-center gap-2">
        <Button asChild variant="ghost" size="sm">
          <Link to="/login">Đăng nhập</Link>
        </Button>
        <Button asChild size="sm" className="rounded-full">
          <Link to="/register">Đăng ký</Link>
        </Button>
      </div>
    );
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="h-10 gap-2 rounded-full pl-1.5 pr-3">
          <span className="grid size-7 place-items-center rounded-full bg-primary text-[11px] font-bold uppercase text-primary-foreground">
            {user.username.slice(0, 2)}
          </span>
          <span className="hidden max-w-32 truncate text-sm sm:inline">
            {user.full_name || user.username}
          </span>
          <ChevronsUpDown className="size-3.5 text-muted-foreground" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="font-normal">
          <p className="truncate text-sm font-medium">{user.full_name || user.username}</p>
          <p className="truncate text-xs text-muted-foreground">{user.email}</p>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={logout} className="cursor-pointer">
          <LogOut className="size-4" />
          Đăng xuất
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const apiStatus = useApiStatus();

  // Trang đăng nhập/đăng ký dùng bố cục toàn màn hình, không có sidebar
  if (AUTH_PATHS.includes(pathname)) {
    return <>{children}</>;
  }

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset className="min-w-0 bg-background">
        <header className="sticky top-0 z-20 flex h-[64px] items-center justify-between gap-3 border-b bg-background/85 px-4 backdrop-blur-md sm:px-6 lg:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <SidebarTrigger className="size-9 rounded-lg" />
            <div className="md:hidden">
              <TeaBrand compact />
            </div>
            <h2 className="hidden truncate font-display text-lg font-semibold md:block">
              {PAGE_TITLES[pathname] ?? "Tea Scholar"}
            </h2>
          </div>
          <div className="flex items-center gap-2 sm:gap-3">
            <StatusPill status={apiStatus} />
            <UserMenu />
          </div>
        </header>
        {apiStatus === "offline" && (
          <div
            role="alert"
            className="flex items-start gap-2 border-b border-destructive/30 bg-destructive/10 px-4 py-2.5 text-sm text-destructive sm:px-6 lg:px-8"
          >
            <WifiOff className="mt-0.5 size-4 shrink-0" />
            <p>
              Không kết nối được máy chủ. Hãy chạy backend (
              <code className="rounded bg-destructive/10 px-1 font-mono text-xs">
                python -m backend.main
              </code>
              ); trang sẽ tự kết nối lại.
            </p>
          </div>
        )}
        <main className="min-h-[calc(100svh-64px)] min-w-0">{children}</main>
      </SidebarInset>
    </SidebarProvider>
  );
}
