import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { apiClient, setStoredToken, clearStoredToken, getStoredToken } from "@/lib/api-client";
import type { UserResponse, UserLoginRequest, UserRegisterRequest } from "@/types/api";

interface AuthContextType {
  user: UserResponse | null;
  loading: boolean;
  login: (data: UserLoginRequest) => Promise<void>;
  register: (data: UserRegisterRequest) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getStoredToken();
    if (!token) {
      setLoading(false);
      return;
    }

    apiClient.auth
      .me()
      .then((userData) => setUser(userData))
      .catch(() => {
        clearStoredToken();
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = async (data: UserLoginRequest) => {
    const res = await apiClient.auth.login(data);
    setStoredToken(res.access_token);
    setUser(res.user);
  };

  const register = async (data: UserRegisterRequest) => {
    await apiClient.auth.register(data);
    // Automatically log in after registration
    await login({
      username_or_email: data.username,
      password: data.password,
    });
  };

  const logout = () => {
    clearStoredToken();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
