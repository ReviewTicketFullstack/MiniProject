import { request } from "@/shared/api";
import type { ID, Order } from "@/entities/order";

export interface OrderCreated extends Order {
  tickets: number;
}

export function createOrder(
  storeId: ID,
  menuId: ID,
  reviewEventApply: boolean
): Promise<OrderCreated> {
  return request<OrderCreated>("/orders", {
    method: "POST",
    body: { storeId, menuId, reviewEventApply },
    auth: true,
  });
}

export function getMyOrders(signal?: AbortSignal): Promise<Order[]> {
  return request<Order[]>("/orders", { auth: true, signal });
}
