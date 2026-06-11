/** Загрузка YouTube IFrame API (один раз на страницу). */
export function loadYouTubeIframeApi(timeoutMs = 15000) {
  if (typeof window === "undefined") {
    return Promise.reject(new Error("no window"));
  }
  if (window.YT?.Player) {
    return Promise.resolve(window.YT);
  }
  if (window.__ytIframeApiPromise) {
    return window.__ytIframeApiPromise;
  }

  window.__ytIframeApiPromise = new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("YouTube IFrame API timeout")), timeoutMs);

    const prev = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = () => {
      clearTimeout(timer);
      prev?.();
      if (window.YT?.Player) resolve(window.YT);
      else reject(new Error("YouTube IFrame API unavailable"));
    };

    if (!document.querySelector('script[src*="youtube.com/iframe_api"]')) {
      const script = document.createElement("script");
      script.src = "https://www.youtube.com/iframe_api";
      script.async = true;
      script.onerror = () => {
        clearTimeout(timer);
        reject(new Error("YouTube IFrame API script failed"));
      };
      document.head.appendChild(script);
    }
  });

  return window.__ytIframeApiPromise;
}
