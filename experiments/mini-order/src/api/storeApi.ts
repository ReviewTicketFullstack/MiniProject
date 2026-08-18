// 가게 목록 및 상세 조회 API 래퍼.
import { request } from "@/shared/api";
import type { Store } from "@/entities/store";
import type { Menu } from "@/entities/menu";

export interface MenuItem extends Menu {}

export interface StoreDetail extends Store {
  menus: MenuItem[];
}

export function getStores(signal?: AbortSignal): Promise<Store[]> {
  return request<Store[]>("/stores", { auth: true, signal });
}

export function getStoreDetail(
  storeId: number,
  signal?: AbortSignal
): Promise<StoreDetail> {
  return request<StoreDetail>(`/stores/${storeId}`, { auth: true, signal });
}
