import { useState } from "react";
import { motion } from "framer-motion";
import { apiPost } from "../api";
import Die3D from "./dice/Die3D";

export default function DiceChoiceModal({ choice, onClose, onDone }) {
  const [busy, setBusy] = useState(false);
  const [cheatDie, setCheatDie] = useState(1);
  const [cheatValue, setCheatValue] = useState(6);
  if (!choice) return null;

  const dice = choice.dice || [];
  const isCheat = choice.type === "cheat";

  const submit = async () => {
    if (busy) return;
    setBusy(true);
    try {
      const body = { cheatDie, cheatValue };
      const data = await apiPost("/turn/confirm-dice", body);
      if (data.user) onDone?.(data);
      onClose();
    } catch (ex) {
      alert(ex.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <motion.div
      className="overlay overlay--casino"
      onClick={onClose}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      <motion.div
        className="modal-panel modal-panel--casino"
        onClick={(e) => e.stopPropagation()}
        initial={{ opacity: 0, y: 24, scale: 0.96 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
      >
        <header>
          <h2>Читерский кубик</h2>
          <button type="button" className="close" onClick={onClose} aria-label="Закрыть">
            ×
          </button>
        </header>
        <div className="modal-body">
          {isCheat && (
            <>
              <p className="casino-section-label">Текущий бросок</p>
              <div className="cheat-dice-preview">
                {[0, 1].map((i) => (
                  <button
                    key={i}
                    type="button"
                    className={`cheat-die-slot${cheatDie === i + 1 ? " selected" : ""}`}
                    onClick={() => setCheatDie(i + 1)}
                  >
                    <Die3D value={dice[i] ?? 1} size="sm" />
                    <label>Кубик {i + 1}</label>
                  </button>
                ))}
              </div>
              <p className="muted">
                Выберите кубик для подмены и новое значение (1–6).
              </p>
              <p className="casino-section-label">Новое значение</p>
              <div className="dice-choice-row">
                {[1, 2, 3, 4, 5, 6].map((n) => (
                  <button
                    key={n}
                    type="button"
                    className={`btn ${cheatValue === n ? "primary" : ""}`}
                    onClick={() => setCheatValue(n)}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </>
          )}
          <div className="inv-action-btns">
            <button
              type="button"
              className="btn primary"
              disabled={busy || (isCheat && !cheatValue)}
              onClick={submit}
            >
              {busy ? "Загрузка..." : "Применить и идти"}
            </button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}
