export type UserRole = "CUSTOMER" | "OWNER";

export interface User {
  id: number;
  email: string;
  displayName: string;
  role: UserRole;
  createdAt?: string;
  tickets?: number;
}

export interface LoginResponse {
  token: string;
  expiresInSeconds: number;
  userId: number;
  displayName: string;
  role: UserRole;
}

export interface AuthContextType {
  user: User | null;
  selectedRole: UserRole | null;
  isRestoring: boolean;
  signin: (result: LoginResponse) => Promise<void>;
  signout: () => void;
  setSelectedRole: (role: UserRole | null) => void;
  updateDisplayName: (displayName: string) => void;
}
