import { useEffect, useState } from "react";
import { apiGet } from "../api";

const FALLBACK = [
  "DOTAG 3 — high limit floor открыт",
  "Консьерж на линии 24/7",
  "Сегодня в зале только премиум-обслуживание",
];

export default function NewsTicker() {
  const [items, setItems] = useState(FALLBACK);

  useEffect(() => {
    apiGet("/news-ticker")
      .then((data) => {
        if (data?.items?.length) setItems(data.items);
      })
      .catch(() => {});
  }, []);

  const line = [...items, ...items].join("    ◆    ");

  return (
    <div className="news-ticker" aria-live="polite">
      <div className="news-ticker__label">
        <span className="news-ticker__live">LIVE</span>
        <span className="news-ticker__title">DOTAG NEWS</span>
      </div>
      <div className="news-ticker__viewport">
        <div className="news-ticker__track">
          <span>{line}</span>
          <span>{line}</span>
        </div>
      </div>
    </div>
  );
}
