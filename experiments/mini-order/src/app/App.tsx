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
