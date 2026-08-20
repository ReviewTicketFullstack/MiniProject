// Mock API 클라이언트: 네트워크 요청을 시뮬레이션하는 가게/메뉴/주문 데이터 반환.
import { messageForErrorCode } from "@/shared/api/errorMessages";
import { clearToken, getToken } from "@/shared/lib/token";
import type { Store } from "@/entities/store";
import type { Menu } from "@/entities/menu";
import type { Order, ID } from "@/entities/order";

// ============ Mock Data ============

const MOCK_STORES: Store[] = [
  {
    id: 1,
    name: "맛있는 카페",
    imageUrl:
      "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Crect fill='%238B6F47' width='200' height='200'/%3E%3Ctext x='50%25' y='50%25' font-size='24' fill='white' text-anchor='middle' dy='.3em'%3E☕%3C/text%3E%3C/svg%3E",
    rating: 4.5,
    reviewCount: 23,
    hasReviewEvent: true,
  },
  {
    id: 2,
    name: "피자 파이",
    imageUrl:
      "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Crect fill='%23E74C3C' width='200' height='200'/%3E%3Ctext x='50%25' y='50%25' font-size='24' fill='white' text-anchor='middle' dy='.3em'%3E🍕%3C/text%3E%3C/svg%3E",
    rating: 4.2,
    reviewCount: 18,
    hasReviewEvent: true,
  },
  {
    id: 3,
    name: "한식당 전",
    imageUrl:
      "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Crect fill='%23C1440E' width='200' height='200'/%3E%3Ctext x='50%25' y='50%25' font-size='24' fill='white' text-anchor='middle' dy='.3em'%3E🍜%3C/text%3E%3C/svg%3E",
    rating: 4.8,
    reviewCount: 42,
    hasReviewEvent: true,
  },
];

const MOCK_MENUS: Record<number, Menu[]> = {
  1: [
    {
      id: 101,
      name: "아메리카노",
      price: 4500,
      imageUrl:
        "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100'%3E%3Crect fill='%23A0826D' width='100' height='100'/%3E%3C/svg%3E",
      reviewEvent: true,
    },
    {
      id: 102,
      name: "카페라떼",
      price: 5500,
      imageUrl:
        "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100'%3E%3Crect fill='%23C4A878' width='100' height='100'/%3E%3C/svg%3E",
      reviewEvent: true,
    },
    {
      id: 103,
      name: "카푸치노",
      price: 5500,
      imageUrl:
        "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100'%3E%3Crect fill='%23D4A574' width='100' height='100'/%3E%3C/svg%3E",
      reviewEvent: true,
    },
  ],
  2: [
    {
      id: 201,
      name: "마르게리따",
      price: 12000,
      imageUrl:
        "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100'%3E%3Crect fill='%23E8B4A6' width='100' height='100'/%3E%3C/svg%3E",
      reviewEvent: true,
    },
    {
      id: 202,
      name: "페퍼로니",
      price: 13000,
      imageUrl:
        "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100'%3E%3Crect fill='%23D84D42' width='100' height='100'/%3E%3C/svg%3E",
      reviewEvent: true,
    },
    {
      id: 203,
      name: "쿠아트로 포르마지",
      price: 14000,
      imageUrl:
        "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100'%3E%3Crect fill='%23F4C589' width='100' height='100'/%3E%3C/svg%3E",
      reviewEvent: true,
    },
  ],
  3: [
    {
      id: 301,
      name: "비빔밥",
      price: 8000,
      imageUrl:
        "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100'%3E%3Crect fill='%23B47F4D' width='100' height='100'/%3E%3C/svg%3E",
      reviewEvent: true,
    },
    {
      id: 302,
      name: "불고기",
      price: 10000,
      imageUrl:
        "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100'%3E%3Crect fill='%238B3A1F' width='100' height='100'/%3E%3C/svg%3E",
      reviewEvent: true,
    },
    {
      id: 303,
      name: "김치찌개",
      price: 7000,
      imageUrl:
        "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100'%3E%3Crect fill='%23C41E3A' width='100' height='100'/%3E%3C/svg%3E",
      reviewEvent: true,
    },
  ],
};

let nextOrderId = 1000;
const memoryOrders: Order[] = [];

export class ApiError extends Error {
  readonly status: number;
  readonly retryable: boolean;
  readonly errorCode?: string;
  readonly detail?: { retryAfterSeconds?: number; imageSimilarity?: number };

  constructor(
    message: string,
    status: number,
    retryable = false,
    errorCode?: string,
    detail?: { retryAfterSeconds?: number; imageSimilarity?: number }
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.retryable = retryable;
    this.errorCode = errorCode;
    this.detail = detail;
  }
}

export interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  query?: Record<string, string>;
  auth?: boolean;
  signal?: AbortSignal;
}

export async function request<T>(
  path: string,
  { method = "GET", body, query, auth = false, signal }: RequestOptions = {}
): Promise<T> {
  if (auth) {
    const token = getToken();
    if (!token) {
      throw new ApiError("로그인이 필요합니다. 다시 로그인해 주세요.", 401);
    }
  }

  // Simulate network delay
  await new Promise((resolve) => setTimeout(resolve, 100));

  // Handle abort signal
  if (signal?.aborted) {
    const error = new DOMException("Aborted", "AbortError");
    throw error;
  }

  // ============ Mock API Routes ============

  // GET /stores - 가게 목록
  if (path === "/stores" && method === "GET") {
    return MOCK_STORES as T;
  }

  // GET /stores/:id - 가게 상세 + 메뉴
  const storeDetailMatch = path.match(/^\/stores\/(\d+)$/);
  if (storeDetailMatch && method === "GET") {
    const storeId = Number(storeDetailMatch[1]);
    const store = MOCK_STORES.find((s) => s.id === storeId);
    if (!store) {
      throw new ApiError("가게를 찾을 수 없습니다.", 404);
    }
    const menus = MOCK_MENUS[storeId] || [];
    return { ...store, menus } as T;
  }

  // POST /orders - 주문 생성
  if (path === "/orders" && method === "POST") {
    const orderBody = body as {
      storeId: number;
      menuId: number;
      reviewEventApply: boolean;
    };
    const store = MOCK_STORES.find((s) => s.id === orderBody.storeId);
    const menu = MOCK_MENUS[orderBody.storeId]?.find(
      (m) => m.id === orderBody.menuId
    );

    if (!store || !menu) {
      throw new ApiError("주문 정보가 잘못되었습니다.", 400);
    }

    const now = new Date();
    const deadline = new Date(now.getTime() + 72 * 60 * 60 * 1000); // 72시간 후

    const order: Order = {
      id: nextOrderId++,
      storeId: store.id,
      storeName: store.name,
      menuName: menu.name,
      price: menu.price,
      hasReviewBadge: orderBody.reviewEventApply,
      reviewStatus: "available",
      reviewDeadline: orderBody.reviewEventApply ? deadline.toISOString() : null,
      createdAt: now.toISOString(),
    };

    memoryOrders.unshift(order);
    return { ...order, tickets: 5 } as T;
  }

  // GET /orders - 주문 목록
  if (path === "/orders" && method === "GET") {
    return memoryOrders as T;
  }

  // GET /stores/:id/reviews - 가게 리뷰
  const reviewsMatch = path.match(/^\/stores\/(\d+)\/reviews$/);
  if (reviewsMatch && method === "GET") {
    // Return empty reviews for now (reviews are not implemented in baseline)
    return [] as T;
  }

  // POST /reviews - 리뷰 생성
  if (path === "/reviews" && method === "POST") {
    // Mock review creation - just acknowledge receipt
    return {
      reviewId: Math.floor(Math.random() * 10000),
      orderId: (body as any).orderId,
      storeId: 1,
      menuId: 1,
      userId: 1,
      reviewRating: (body as any).reviewRating,
      reviewContent: (body as any).reviewContent,
      reviewImageUrl: "data:image/svg+xml,%3Csvg%3E%3C/svg%3E",
      reviewCreatedAt: new Date().toISOString(),
      imageSimilarity: 0.95,
      compareImageUrl: "data:image/svg+xml,%3Csvg%3E%3C/svg%3E",
      tickets: 5,
    } as T;
  }

  throw new ApiError("요청을 처리하지 못했습니다.", 400);
}
