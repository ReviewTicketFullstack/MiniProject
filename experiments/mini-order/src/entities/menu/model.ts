// 메뉴 도메인 모델 (이름, 가격).
export interface Menu {
  id: number;
  name: string;
  price: number;
  imageUrl: string | null;
  reviewEvent: boolean;
}
