import { useEffect, useState } from "react";

const RESULT_MS = 2800;

export default function RewardDiceModal({ dice, actorUsername, onDone }) {
  const value = dice?.[0] ?? 1;
  const [shown, setShown] = useState(1);
  const [phase, setPhase] = useState("rolling");

  useEffect(() => {
    setPhase("rolling");
    let step = 0;
    const t = setInterval(() => {
      setShown(1 + Math.floor(Math.random() * 3));
      step += 1;
      if (step > 14) {
        clearInterval(t);
        setShown(value);
        setPhase("result");
      }
    }, 80);
    return () => clearInterval(t);
  }, [value]);

  useEffect(() => {
    if (phase !== "result") return undefined;
    const t = setTimeout(() => onDone?.(), RESULT_MS);
    return () => clearTimeout(t);
  }, [phase, onDone]);

  const wheelsLabel =
    value === 1 ? "1 колесо предметов" : `${value} колеса предметов`;

  return (
    <div className="overlay overlay-spectate">
      <div className="modal-square dice-modal reward-dice-modal">
        <p className="spectate-actor reward-dice-title">Призовой кубик</p>
        <p className="muted reward-dice-sub">
          {actorUsername} · награда за прохождение игры
        </p>
        <div className="dice-row">
          <div className="die die-single die-reward">{shown}</div>
        </div>
        {phase === "result" && (
          <p className="reward-dice-result">
            Выпало: <strong>{value}</strong> — {wheelsLabel}
          </p>
        )}
        {phase === "rolling" && (
          <p className="muted dice-rolling-hint">Крутим призовой кубик…</p>
        )}
      </div>
    </div>
  );
}
