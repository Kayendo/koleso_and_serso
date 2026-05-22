import { useEffect, useState } from "react";

const RESULT_MS = 4200;

export default function DiceModal({
  dice,
  rawDice,
  actorUsername,
  factors = [],
  steps,
  label,
  showEffects = true,
  onDone,
}) {
  const faces =
    rawDice?.length >= 2 ? rawDice : dice?.length >= 2 ? dice : dice;
  const [shown, setShown] = useState([1, 1]);
  const [phase, setPhase] = useState("rolling");

  useEffect(() => {
    if (!faces?.length) return undefined;
    setPhase("rolling");
    let step = 0;
    const t = setInterval(() => {
      const r = () => 1 + Math.floor(Math.random() * 6);
      setShown(faces.length === 1 ? [r()] : [r(), r()]);
      step += 1;
      if (step > 12) {
        clearInterval(t);
        setShown(faces);
        setPhase("result");
      }
    }, 80);
    return () => clearInterval(t);
  }, [faces]);

  useEffect(() => {
    if (phase !== "result") return undefined;
    const t = setTimeout(() => onDone?.(), RESULT_MS);
    return () => clearTimeout(t);
  }, [phase, onDone]);

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
          {actorUsername} {phase === "rolling" ? "бросает кубики" : "бросил кубики"}
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
                    factors.map((f, i) => <li key={i}>{f}</li>)
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
