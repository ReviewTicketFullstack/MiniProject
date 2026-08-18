import type { ISODateTime } from "./model";

export function getRemainingReviewTime(reviewDeadline: ISODateTime): number {
  const now = new Date().getTime();
  const deadline = new Date(reviewDeadline).getTime();
  return Math.max(0, deadline - now);
}

export function formatTimeRemaining(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes.toString().padStart(2, "0")}:${seconds
    .toString()
    .padStart(2, "0")}`;
}

export function formatOrderDate(createdAt: ISODateTime): string {
  return new Date(createdAt).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}
