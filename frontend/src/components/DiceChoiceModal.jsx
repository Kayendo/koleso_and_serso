import { useState } from "react";
import { apiPost } from "../api";

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
    <div className="overlay" onClick={onClose}>
      <div
        className="modal-panel"
        onClick={(e) => e.stopPropagation()}
      >
        <header>
          <h2>Читерский кубик</h2>
          <button type="button" className="close" onClick={onClose}>
            ×
          </button>
        </header>
        <div className="modal-body">
          {isCheat && (
            <>
              <p className="muted">
                Бросок: кубик 1 = {dice[0]}, кубик 2 = {dice[1]}. Выберите,
                какой заменить и на какое значение (1–6). Итог хода станет
                известен после подтверждения.
              </p>
              <div className="dice-choice-row">
                <button
                  type="button"
                  className={`btn ${cheatDie === 1 ? "primary" : ""}`}
                  onClick={() => setCheatDie(1)}
                >
                  Кубик 1 ({dice[0]})
                </button>
                <button
                  type="button"
                  className={`btn ${cheatDie === 2 ? "primary" : ""}`}
                  onClick={() => setCheatDie(2)}
                >
                  Кубик 2 ({dice[1]})
                </button>
              </div>
              <label className="field-label">Новое значение (1–6)</label>
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
      </div>
    </div>
  );
}
