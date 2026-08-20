// 가게 목록 캐싱.
import type { Store } from "./model";

export const STORE_CACHE_KEY = "review_ticket_stores";

export function getCachedStores(): Store[] | null {
  const cached = localStorage.getItem(STORE_CACHE_KEY);
  if (!cached) return null;

  try {
    const { stores, timestamp } = JSON.parse(cached);
    if (stores.length === 0) return null;

    const nextMidnight = new Date();
    nextMidnight.setHours(24, 0, 0, 0);

    if (timestamp < nextMidnight.getTime()) {
      return stores;
    }
  } catch {
    localStorage.removeItem(STORE_CACHE_KEY);
  }

  return null;
}

export function setCachedStores(stores: Store[]) {
  const nextMidnight = new Date();
  nextMidnight.setHours(24, 0, 0, 0);

  localStorage.setItem(
    STORE_CACHE_KEY,
    JSON.stringify({
      stores,
      timestamp: Date.now(),
      expiresAt: nextMidnight.getTime(),
    })
  );
}

export function clearStoreCache() {
  localStorage.removeItem(STORE_CACHE_KEY);
}
