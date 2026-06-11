import { useEffect, useRef, useState } from "react";
import { apiGet } from "../api";

const FALLBACK = [
  "DOTAG 3 — high limit floor открыт",
  "Консьерж на линии 24/7",
  "Сегодня в зале только премиум-обслуживание",
];

/** Пикселей в секунду — комфортно читать русский текст */
const PX_PER_SEC = 60;
const MIN_DURATION_SEC = 75;

export default function NewsTicker() {
  const [items, setItems] = useState(FALLBACK);
  const trackRef = useRef(null);
  const [durationSec, setDurationSec] = useState(180);

  useEffect(() => {
    apiGet("/news-ticker")
      .then((data) => {
        if (data?.items?.length) setItems(data.items);
      })
      .catch(() => {});
  }, []);

  const line = [...items, ...items].join("    ◆    ");

  useEffect(() => {
    const track = trackRef.current;
    if (!track) return undefined;

    const measure = () => {
      const span = track.querySelector("span");
      if (!span) return;
      const width = span.scrollWidth;
      if (width > 0) {
        setDurationSec(Math.max(MIN_DURATION_SEC, width / PX_PER_SEC));
      }
    };

    measure();
    const id = requestAnimationFrame(measure);

    let ro;
    if (typeof ResizeObserver !== "undefined") {
      ro = new ResizeObserver(measure);
      ro.observe(track);
    }

    return () => {
      cancelAnimationFrame(id);
      ro?.disconnect();
    };
  }, [line]);

  return (
    <div className="news-ticker" aria-live="polite">
      <div className="news-ticker__label">
        <span className="news-ticker__live">LIVE</span>
        <span className="news-ticker__title">DOTAG NEWS</span>
      </div>
      <div className="news-ticker__viewport">
        <div
          ref={trackRef}
          className="news-ticker__track"
          style={{ animationDuration: `${durationSec}s` }}
        >
          <span>{line}</span>
          <span>{line}</span>
        </div>
      </div>
    </div>
  );
}
