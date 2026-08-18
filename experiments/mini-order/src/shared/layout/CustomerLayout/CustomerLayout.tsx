import { NavLink, Outlet } from "react-router-dom";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  isActive ? "font-bold underline" : "underline";

export function CustomerLayout() {
  return (
    <div className="mx-auto max-w-2xl">
      <header className="border-b border-gray-400 p-4">
        <h1 className="mb-2 text-xl font-bold">mini-order</h1>
        <nav className="flex gap-4">
          <NavLink to="/home" className={linkClass}>
            홈
          </NavLink>
          <NavLink to="/order-history" className={linkClass}>
            주문내역
          </NavLink>
        </nav>
      </header>

      <main>
        <Outlet />
      </main>
    </div>
  );
}
