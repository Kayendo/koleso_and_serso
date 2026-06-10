/** Отображаемое имя игрока (логин — отдельно). */
export function playerName(p) {
  if (!p) return "?";
  return p.displayName || p.username || "?";
}

/** Имя из payload хода / сокета. */
export function payloadPlayerName(payload, fallback) {
  return (
    payload?.displayName ||
    payload?.username ||
    fallback?.displayName ||
    fallback?.username ||
    "?"
  );
}
