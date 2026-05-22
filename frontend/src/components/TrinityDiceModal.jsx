import { useEffect, useState } from "react";
import { apiPost } from "../api";

const ROLL_MS = 1600;

export default function TrinityDiceModal({ onClose, onDone }) {
  const [phase, setPhase] = useState("rolling");
  const [shown, setShown] = useState([1, 1, 1]);
  const [dice, setDice] = useState([]);
  const [picked, setPicked] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let step = 0;
    const t = setInterval(() => {
      setShown([
        1 + Math.floor(Math.random() * 6),
        1 + Math.floor(Math.random() * 6),
        1 + Math.floor(Math.random() * 6),
      ]);
      step += 1;
      if (step > 18) {
        clearInterval(t);
        apiPost("/turn/reveal-trinity-dice", {})
          .then((data) => {
            const d = data.dice || [];
            setDice(d);
            setShown(d.length >= 3 ? d : shown);
            setPhase("pick");
          })
          .catch((ex) => setError(ex.message));
      }
    }, 80);
    return () => clearInterval(t);
  }, []);

  const toggle = (index) => {
    setPicked((prev) => {
      if (prev.includes(index)) {
        return prev.filter((i) => i !== index);
      }
      if (prev.length >= 2) {
        return [prev[1], index];
      }
      return [...prev, index];
    });
  };

  const submit = async () => {
    if (busy || picked.length !== 2) return;
    setBusy(true);
    try {
      const body = { trinityPick: picked.map((i) => dice[i]) };
      const data = await apiPost("/turn/confirm-dice", body);
      if (data.user) onDone?.(data);
      onClose();
    } catch (ex) {
      setError(ex.message);
    } finally {
      setBusy(false);
    }
  };

  const display = phase === "rolling" ? shown : dice;

  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal-panel" onClick={(e) => e.stopPropagation()}>
        <header>
          <h2>Бог любит троицу</h2>
          <button type="button" className="close" onClick={onClose}>
            ×
          </button>
        </header>
        <div className="modal-body">
          {phase === "rolling" && (
            <p className="muted">Бросаем три кубика…</p>
          )}
          {phase === "pick" && (
            <p className="muted">Выберите два кубика из трёх:</p>
          )}
          <div className="dice-choice-row dice-trinity-row">
            {display.map((v, i) => (
              <button
                key={i}
                type="button"
                className={`btn die-btn ${picked.includes(i) ? "primary" : ""}`}
                disabled={phase === "rolling"}
                onClick={() => phase === "pick" && toggle(i)}
              >
                {v}
              </button>
            ))}
          </div>
          {phase === "pick" && (
            <p className="muted">
              Выбрано:{" "}
              {picked.length
                ? picked.map((i) => dice[i]).join(" + ")
                : "—"}
            </p>
          )}
          {error && <p className="error">{error}</p>}
          {phase === "pick" && (
            <div className="inv-action-btns">
              <button
                type="button"
                className="btn primary"
                disabled={busy || picked.length !== 2}
                onClick={submit}
              >
                {busy ? "Загрузка..." : "Применить и идти"}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
