// 범용 버튼 컴포넌트.
import type { ButtonHTMLAttributes } from "react";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {}

export function Button({ children, className, ...props }: ButtonProps) {
  return (
    <button
      className={`border border-gray-600 px-4 py-2 disabled:opacity-50 ${
        className || ""
      }`}
      {...props}
    >
      {children}
    </button>
  );
}
