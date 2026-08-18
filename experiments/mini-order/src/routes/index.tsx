import { Routes, Route, Navigate } from "react-router-dom";
import { CustomerLayout } from "@/shared/layout";
import { useAuth } from "@/app/providers";
import { Loading } from "@/shared/ui";
import HomePage from "@/pages/customer/HomePage";
import OrderHistoryPage from "@/pages/customer/OrderHistoryPage";

function ProtectedRoute({
  children,
  role,
}: {
  children: React.ReactNode;
  role: "CUSTOMER" | "OWNER";
}) {
  const { user, isRestoring } = useAuth();

  if (isRestoring) {
    return <Loading />;
  }

  if (!user) {
    return <Navigate to="/home" replace />;
  }

  if (user.role !== role) {
    return <Navigate to="/home" replace />;
  }

  return children;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/home" replace />} />

      <Route
        element={
          <ProtectedRoute role="CUSTOMER">
            <CustomerLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/home" element={<HomePage />} />
        <Route path="/order-history" element={<OrderHistoryPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/home" replace />} />
    </Routes>
  );
}
