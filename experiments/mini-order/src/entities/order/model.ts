export type ID = number;
export type ISODateTime = string;
export type ReviewStatus = "available" | "not_available" | "expired" | "done";

export interface Order {
  id: ID;
  storeId: ID;
  storeName: string;
  menuName: string;
  price: number;
  hasReviewBadge: boolean;
  reviewStatus: ReviewStatus;
  reviewDeadline: ISODateTime | null;
  createdAt: ISODateTime;
}
