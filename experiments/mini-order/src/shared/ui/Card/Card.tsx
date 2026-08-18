// 범용 카드 컴포넌트.
import type { HTMLAttributes } from "react";

export interface CardProps extends HTMLAttributes<HTMLDivElement> {}

export function Card({ children, className, ...props }: CardProps) {
  return (
    <div className={`border border-gray-400 ${className || ""}`} {...props}>
      {children}
    </div>
  );
}
