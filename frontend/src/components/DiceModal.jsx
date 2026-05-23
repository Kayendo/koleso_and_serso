import { useEffect, useMemo, useRef, useState } from "react";

const ROLL_TICKS = 6;
const ROLL_MS = 50;

export default function DiceModal({
  dice,
  rawDice,
  actorUsername,
  factors = [],
  steps,
  label,
  showEffects = true,
  onRollComplete,
}) {
  const faces = useMemo(() => {
    const d = rawDice?.length >= 2 ? rawDice : dice?.length >= 2 ? dice : dice;
    return Array.isArray(d) ? [...d] : [1, 1];
  }, [rawDice, dice]);

  const facesKey = useMemo(() => faces.join(","), [faces]);
  const onCompleteRef = useRef(onRollComplete);

  useEffect(() => {
    onCompleteRef.current = onRollComplete;
  }, [onRollComplete]);

  const [shown, setShown] = useState([1, 1]);
  const [phase, setPhase] = useState("rolling");

  useEffect(() => {
    if (!facesKey) return undefined;
    setPhase("rolling");
    let step = 0;
    const t = setInterval(() => {
      const r = () => 1 + Math.floor(Math.random() * 6);
      setShown(faces.length === 1 ? [r()] : [r(), r()]);
      step += 1;
      if (step >= ROLL_TICKS) {
        clearInterval(t);
        setShown(faces);
        setPhase("result");
        onCompleteRef.current?.();
      }
    }, ROLL_MS);
    return () => clearInterval(t);
  }, [facesKey, faces.length]);

  if (!dice?.length) return null;

  const faceSum =
    faces.length === 1 ? shown[0] : shown[0] + (shown[1] ?? 0);
  const totalSteps = steps ?? faceSum;
  const stepsChanged = totalSteps !== faceSum;
  const hasModifiers = showEffects && (factors.length > 0 || stepsChanged);

  return (
    <div className="overlay overlay-spectate">
      <div className="modal-square dice-modal">
        <p className="spectate-actor">
          {actorUsername}{" "}
          {phase === "rolling" ? "бросает кубики" : "бросил кубики"}
        </p>
        <div className="dice-row">
          {faces.length === 1 ? (
            <div className="die die-single">{shown[0]}</div>
          ) : (
            <>
              <div className="die">{shown[0]}</div>
              <div className="die">{shown[1]}</div>
            </>
          )}
        </div>
        {phase === "result" && (
          <>
            {stepsChanged && (
              <p className="dice-sum">
                {faceSum} → <strong>{totalSteps}</strong> клеток
                {label ? ` (${label})` : ""}
              </p>
            )}
            {hasModifiers ? (
              <div className="dice-effects-panel">
                <p className="dice-effects-title">Что изменило бросок</p>
                <ul className="dice-effects-list">
                  {factors.length > 0 ? (
                    factors.map((f, i) => (
                      <li key={i}>{f}</li>
                    ))
                  ) : (
                    <li className="muted">Сумма изменена модификаторами</li>
                  )}
                </ul>
              </div>
            ) : (
              <p className="dice-effects-none muted">Без доп. эффектов к броску</p>
            )}
          </>
        )}
        {phase === "rolling" && (
          <p className="muted dice-rolling-hint">Бросок…</p>
        )}
      </div>
    </div>
  );
}
