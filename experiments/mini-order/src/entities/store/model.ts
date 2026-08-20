// 가게 도메인 모델 (이름, 평점, 리뷰).
export interface Store {
  id: number;
  name: string;
  imageUrl: string | null;
  rating: number;
  reviewCount: number;
  hasReviewEvent: boolean;
}
