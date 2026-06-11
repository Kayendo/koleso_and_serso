import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { apiPost } from "../api";
import Die3D from "./dice/Die3D";
import DiceTableSpectacle from "./dice/DiceTableSpectacle";

export default function TrinityDiceModal({ onClose, onDone }) {
  const [phase, setPhase] = useState("rolling");
  const [dice, setDice] = useState(null);
  const [picked, setPicked] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    apiPost("/turn/reveal-trinity-dice", {})
      .then((data) => setDice(data.dice || [1, 1, 1]))
      .catch((ex) => setError(ex.message));
  }, []);

  const toggle = (index) => {
    setPicked((prev) => {
      if (prev.includes(index)) return prev.filter((i) => i !== index);
      if (prev.length >= 2) return [prev[1], index];
      return [...prev, index];
    });
  };

  const submit = async () => {
    if (busy || picked.length !== 2 || !dice) return;
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

  if (phase === "rolling") {
    return (
      <motion.div
        className="overlay overlay-spectate overlay--casino"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        <DiceTableSpectacle
          finalValues={dice || [1, 1, 1]}
          actorUsername="Троица"
          phaseLabel={dice ? "три кубика на сукне" : "бросаем три кубика…"}
          indefiniteRoll={!dice}
          autoRoll={!!dice}
          onRollComplete={dice ? () => setPhase("pick") : undefined}
          compact
        />
        {error && <p className="error dice-table-error">{error}</p>}
      </motion.div>
    );
  }

  return (
    <motion.div
      className="overlay overlay--casino"
      onClick={onClose}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      <motion.div
        className="modal-panel modal-panel--casino trinity-modal"
        onClick={(e) => e.stopPropagation()}
        initial={{ opacity: 0, y: 28, scale: 0.96 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
      >
        <header>
          <h2>Бог любит троицу</h2>
          <button type="button" className="close" onClick={onClose} aria-label="Закрыть">
            ×
          </button>
        </header>
        <div className="modal-body">
          <p className="casino-section-label">Выберите два кубика</p>
          <div className="trinity-pick-felt">
            {(dice || []).map((v, i) => (
              <button
                key={i}
                type="button"
                className={`trinity-pick-die ${picked.includes(i) ? "selected" : ""}`}
                onClick={() => toggle(i)}
              >
                <Die3D value={v} size="sm" />
                <span className="trinity-pick-label">
                  {picked.includes(i) ? "✓ выбран" : `Кубик ${i + 1}`}
                </span>
              </button>
            ))}
          </div>
          <p className="trinity-pick-sum muted">
            Сумма:{" "}
            {picked.length === 2 && dice
              ? `${picked.map((i) => dice[i]).join(" + ")} = ${picked.reduce((s, i) => s + dice[i], 0)}`
              : "выберите два"}
          </p>
          {error && <p className="error">{error}</p>}
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
        </div>
      </motion.div>
    </motion.div>
  );
}
