/**
 * Таймеры по wall-clock — работают в свёрнутой вкладке (в отличие от rAF).
 */

export function sleep(ms) {
  return new Promise((resolve) => {
    if (ms <= 0) {
      resolve();
      return;
    }
    const end = performance.now() + ms;
    const tick = () => {
      if (performance.now() >= end) resolve();
      else setTimeout(tick, document.hidden ? 50 : 16);
    };
    setTimeout(tick, document.hidden ? 50 : 16);
  });
}

/**
 * Анимация 0..1 за durationMs; onFrame(t), onDone().
 */
export function animateProgress(durationMs, onFrame, onDone) {
  const start = performance.now();
  const step = () => {
    const t = Math.min(1, (performance.now() - start) / durationMs);
    onFrame(t);
    if (t < 1) {
      if (document.hidden) setTimeout(step, 50);
      else requestAnimationFrame(step);
    } else {
      onDone?.();
    }
  };
  if (document.hidden) setTimeout(step, 0);
  else requestAnimationFrame(step);
}
