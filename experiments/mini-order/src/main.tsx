// 애플리케이션 진입점: React 렌더링 시작.
import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "@/app";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
