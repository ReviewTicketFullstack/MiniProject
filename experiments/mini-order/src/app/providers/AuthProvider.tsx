import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import type {
  User,
  UserRole,
  LoginResponse,
  AuthContextType,
} from "@/entities/user";
import { getToken, saveToken } from "@/shared/lib/token";

const AuthContext = createContext<AuthContextType | null>(null);

// Mock authenticated customer for baseline
const MOCK_USER: User = {
  id: 1,
  email: "customer@example.com",
  displayName: "테스트 고객",
  role: "CUSTOMER",
  tickets: 5,
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [selectedRole, setSelectedRole] = useState<UserRole | null>(null);
  const [isRestoring, setIsRestoring] = useState(true);

  useEffect(() => {
    // Simulate minimal session restoration
    const token = getToken();
    if (token) {
      setUser(MOCK_USER);
    } else {
      // Set up mock token and user for baseline
      saveToken("mock-token-for-baseline", 86400 * 365); // 1 year
      setUser(MOCK_USER);
    }
    setIsRestoring(false);
  }, []);

  const signin = async (result: LoginResponse) => {
    saveToken(result.token, result.expiresInSeconds);
    setUser({
      id: result.userId,
      email: "customer@example.com",
      displayName: result.displayName,
      role: result.role,
      tickets: 5,
    });
    setSelectedRole(null);
  };

  const signout = () => {
    setUser(null);
    setSelectedRole(null);
  };

  const updateDisplayName = (displayName: string) => {
    setUser((current) =>
      current ? { ...current, displayName } : current
    );
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        selectedRole,
        isRestoring,
        setSelectedRole,
        signin,
        signout,
        updateDisplayName,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context)
    throw new Error("useAuth는 AuthProvider 내부에서만 사용할 수 있습니다.");
  return context;
}
