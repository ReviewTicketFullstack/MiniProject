export interface Store {
  id: number;
  name: string;
  imageUrl: string | null;
  rating: number;
  reviewCount: number;
  hasReviewEvent: boolean;
}
