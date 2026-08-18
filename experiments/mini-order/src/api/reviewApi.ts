// 리뷰 API 래퍼 (현재 미사용).
import { request } from "@/shared/api";
import type { ID, ISODateTime } from "@/entities/order";

export interface ReviewCreated {
  reviewId: ID;
  orderId: ID;
  storeId: ID;
  menuId: ID;
  userId: ID;
  reviewRating: number;
  reviewContent: string;
  reviewImageUrl: string;
  reviewCreatedAt: ISODateTime;
  imageSimilarity: number;
  compareImageUrl: string;
  tickets: number;
}

export interface PublicReview {
  reviewId: ID;
  menuId: ID;
  menuName: string;
  displayName: string;
  reviewRating: number;
  reviewContent: string;
  reviewImageUrl: string;
  reviewCreatedAt: ISODateTime;
}

export function createReview(
  orderId: ID,
  reviewRating: number,
  reviewContent: string,
  image: File
): Promise<ReviewCreated> {
  const form = new FormData();
  form.append("orderId", String(orderId));
  form.append("reviewRating", String(reviewRating));
  form.append("reviewContent", reviewContent);
  form.append("image", image);

  return request<ReviewCreated>("/reviews", {
    method: "POST",
    body: form,
    auth: true,
  });
}

export function getStoreReviews(
  storeId: ID,
  signal?: AbortSignal
): Promise<PublicReview[]> {
  return request<PublicReview[]>(`/stores/${storeId}/reviews`, {
    auth: true,
    signal,
  });
}
