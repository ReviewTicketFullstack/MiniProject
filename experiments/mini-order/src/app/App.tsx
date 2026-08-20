// 루트 컴포넌트: 라우팅, 인증 제공자 래핑.
import { BrowserRouter } from "react-router-dom";
import { AppRoutes } from "@/routes";
import { AuthProvider } from "./providers";

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}
