import { useEffect, useState } from "react";
import { getMyOrders } from "@/api/orderApi";
import { getOrderHistory, replaceOrderHistory } from "@/entities/order";
import { ApiError } from "@/shared/api";
import type { Order } from "@/entities/order";

export default function OrderHistoryPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    getMyOrders(controller.signal)
      .then((serverOrders) => {
        setOrders(serverOrders);
        replaceOrderHistory(serverOrders);
      })
      .catch((e: unknown) => {
        if (e instanceof DOMException && e.name === "AbortError") return;

        const cached = getOrderHistory();
        setOrders(cached);
        setError(
          cached.length > 0
            ? "서버에 연결하지 못해 저장된 내역을 보여줍니다."
            : e instanceof ApiError
              ? e.message
              : "주문내역을 불러오지 못했습니다."
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false);
      });

    return () => controller.abort();
  }, []);

  return (
    <div className="p-4">
      <h2 className="mb-4 text-lg font-bold">주문내역</h2>

      {error && <p className="mb-4 text-sm text-red-700">{error}</p>}

      {isLoading ? (
        <p>불러오는 중...</p>
      ) : orders.length === 0 ? (
        <p>주문내역이 없습니다.</p>
      ) : (
        <ul className="border border-gray-400">
          {orders.map((order) => (
            <li
              key={order.id}
              className="border-b border-gray-300 p-3 last:border-b-0"
            >
              <div>주문번호: {order.id}</div>
              <div>가게: {order.storeName}</div>
              <div>메뉴: {order.menuName}</div>
              <div>가격: {order.price}원</div>
              <div>상태: {order.reviewStatus}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
