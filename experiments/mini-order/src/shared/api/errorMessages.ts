export function messageForErrorCode(code?: string): string {
  switch (code) {
    case "IMAGE_NOT_MATCHED":
      return "주문한 메뉴와 다른 사진으로 보입니다.";
    case "REVIEW_PERIOD_EXPIRED":
      return "리뷰 작성 시간이 지났습니다.";
    case "REVIEW_ALREADY_EXISTS":
      return "이미 리뷰를 작성한 주문입니다.";
    case "REVIEW_EVENT_NOT_APPLIED":
      return "리뷰이벤트에 참여하지 않은 주문입니다.";
    case "IMAGE_TOO_SMALL":
      return "사진 화질이 너무 낮습니다.";
    case "FILE_TOO_LARGE":
      return "사진 용량이 너무 큽니다.";
    case "UNSUPPORTED_IMAGE_TYPE":
      return "지원하지 않는 사진 형식입니다.";
    case "AI_SERVER_UNAVAILABLE":
      return "사진 확인이 지연되고 있습니다.";
    default:
      return "";
  }
}
