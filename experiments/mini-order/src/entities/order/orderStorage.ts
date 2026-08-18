import type { Order } from "./model";

const ORDERS_KEY = "review_ticket_orders";

export function saveOrder(order: Order): void {
  const orders = getOrderHistory().filter((saved) => saved.id !== order.id);
  orders.unshift(order);
  writeOrders(orders);
}

export function replaceOrderHistory(orders: Order[]): void {
  writeOrders(orders);
}

export function getOrderHistory(): Order[] {
  const stored = localStorage.getItem(ORDERS_KEY);
  if (!stored) return [];

  try {
    const parsed: unknown = JSON.parse(stored);
    if (!Array.isArray(parsed))
      throw new Error("주문 사본이 배열이 아닙니다.");

    return parsed as Order[];
  } catch {
    localStorage.removeItem(ORDERS_KEY);
    return [];
  }
}

function writeOrders(orders: Order[]): void {
  try {
    localStorage.setItem(ORDERS_KEY, JSON.stringify(orders));
  } catch {
    // 저장이 막힌 환경에서는 사본 없이 동작한다.
  }
}
