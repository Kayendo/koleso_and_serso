import {
  cellCenterPercent,
  inwardArcUnit,
  tokenSizeFraction,
} from "./boardLayout";
import { animateProgress } from "./wallClock";

function easeSmooth(t) {
  return t * t * (3 - 2 * t);
}

function animateLeg({
  userId,
  avatarUrl,
  fromCell,
  toCell,
  durationMs,
  setFlyingToken,
}) {
  const from = cellCenterPercent(fromCell);
  const to = cellCenterPercent(toCell);
  const inward = inwardArcUnit(toCell);
  const arcScale = 1.8;
  const sizeFrac = tokenSizeFraction(1);

  setFlyingToken({
    userId,
    avatarUrl,
    left: from.left,
    top: from.top,
    sizeFrac,
  });

  return new Promise((resolve) => {
    animateProgress(
      durationMs,
      (t) => {
        const e = easeSmooth(t);
        const arc = 4 * e * (1 - e);
        const left =
          from.left + (to.left - from.left) * e + inward.x * arcScale * arc;
        const top =
          from.top + (to.top - from.top) * e + inward.y * arcScale * arc;
        setFlyingToken({
          userId,
          avatarUrl,
          left,
          top,
          sizeFrac,
        });
      },
      resolve
    );
  });
}

export function runTokenPath({
  userId,
  path,
  fromPosition,
  stepMs,
  setFlyingToken,
  setAnimPositions,
  setPlayers,
  avatarUrl,
}) {
  if (!path?.length) return Promise.resolve();

  return new Promise((resolve) => {
    let from = fromPosition;

    const run = async () => {
      setAnimPositions((prev) => ({ ...prev, [userId]: from }));

      for (const next of path) {
        await animateLeg({
          userId,
          avatarUrl,
          fromCell: from,
          toCell: next,
          durationMs: stepMs,
          setFlyingToken,
        });
        setAnimPositions((prev) => ({ ...prev, [userId]: next }));
        setPlayers((prev) =>
          prev.map((u) => (u.id === userId ? { ...u, position: next } : u))
        );
        from = next;
      }

      setFlyingToken(null);
      resolve();
    };

    run();
  });
}
