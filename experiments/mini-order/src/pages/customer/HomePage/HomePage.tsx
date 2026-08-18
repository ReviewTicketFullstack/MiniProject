import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getStoreDetail } from "@/api/storeApi";
import { createOrder } from "@/api/orderApi";
import { ApiError } from "@/shared/api";
import { Button } from "@/shared/ui";
import type { Menu } from "@/entities/menu";

const STORE_ID = 1;

export default function HomePage() {
  const navigate = useNavigate();
  const [menus, setMenus] = useState<Menu[]>([]);
  const [selectedMenuId, setSelectedMenuId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isOrdering, setIsOrdering] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    getStoreDetail(STORE_ID, controller.signal)
      .then((detail) => setMenus(detail.menus))
      .catch((e: unknown) => {
        if (e instanceof DOMException && e.name === "AbortError") return;
        setError(
          e instanceof ApiError ? e.message : "메뉴를 불러오지 못했습니다."
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false);
      });

    return () => controller.abort();
  }, []);

  function handleOrder() {
    if (selectedMenuId === null) return;

    setIsOrdering(true);
    setError("");

    createOrder(STORE_ID, selectedMenuId, false)
      .then(() => navigate("/order-history"))
      .catch((e: unknown) => {
        setError(
          e instanceof ApiError ? e.message : "주문에 실패했습니다."
        );
        setIsOrdering(false);
      });
  }

  return (
    <div className="p-4">
      <h2 className="mb-4 text-lg font-bold">메뉴</h2>

      {error && <p className="mb-4 text-sm text-red-700">{error}</p>}

      {isLoading ? (
        <p>불러오는 중...</p>
      ) : (
        <>
          <ul className="mb-4 border border-gray-400">
            {menus.map((menu) => (
              <li key={menu.id} className="border-b border-gray-300 last:border-b-0">
                <label className="flex items-center gap-3 p-3">
                  <input
                    type="radio"
                    name="menu"
                    value={menu.id}
                    checked={selectedMenuId === menu.id}
                    onChange={() => setSelectedMenuId(menu.id)}
                  />
                  <span className="flex-1">{menu.name}</span>
                  <span>{menu.price}원</span>
                </label>
              </li>
            ))}
          </ul>

          <Button
            onClick={handleOrder}
            disabled={selectedMenuId === null || isOrdering}
          >
            {isOrdering ? "주문 중..." : "주문하기"}
          </Button>
        </>
      )}
    </div>
  );
}
