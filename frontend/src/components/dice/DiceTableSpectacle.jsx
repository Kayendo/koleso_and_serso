import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { apiPost } from "../../api";
import VipChip from "../../ui/VipChip";
import PhysicsDiceScene from "./PhysicsDiceScene";

/**
 * Казино-спектакль: физический бросок → результат = то, что легло на сукне.
 */
export default function DiceTableSpectacle({
  finalValues,
  actorUsername,
  phaseLabel,
  subtitle,
  children,
  requireAccept = false,
  onDone,
  onRollComplete,
  autoRoll = true,
  indefiniteRoll = false,
  compact = false,
  physicsRoll = false,
  rollKey = 0,
  onPhysicsConfirmed,
}) {
  const count = Math.max(1, finalValues?.length || 2);
  const [phase, setPhase] = useState(
    indefiniteRoll ? "rolling" : physicsRoll ? "rolling" : "result"
  );
  const [displayValues, setDisplayValues] = useState(finalValues || null);
  const confirmingRef = useRef(false);

  useEffect(() => {
    if (indefiniteRoll) {
      setPhase("rolling");
      return undefined;
    }
    if (physicsRoll) {
      setDisplayValues(null);
      setPhase("rolling");
      confirmingRef.current = false;
      return undefined;
    }
    if (finalValues?.length) {
      setDisplayValues(finalValues);
      setPhase("result");
      return undefined;
    }
    if (!autoRoll) {
      setDisplayValues(finalValues || [1]);
      setPhase("result");
      return undefined;
    }
    setDisplayValues(finalValues || [1, 1]);
    setPhase("rolling");
    return undefined;
  }, [finalValues?.join(","), autoRoll, indefiniteRoll, physicsRoll, rollKey]);

  const handlePhysicsSettled = async (values) => {
    if (confirmingRef.current) return;
    confirmingRef.current = true;

    if (physicsRoll) {
      try {
        const data = await apiPost("/turn/confirm-dice-physics", { dice: values });
        setDisplayValues(data.dice || values);
        setPhase("result");
        onPhysicsConfirmed?.(data);
        if (!requireAccept && onRollComplete) {
          setTimeout(() => onRollComplete(), 400);
        }
      } catch {
        confirmingRef.current = false;
      }
      return;
    }

    setDisplayValues(values);
    setPhase("result");
    if (!requireAccept && onRollComplete) {
      setTimeout(() => onRollComplete(), 300);
    }
  };

  const rolling = phase === "rolling";
  const showValues = displayValues || finalValues || [1, 1];

  return (
    <motion.div
      className={`dice-table-spectacle${compact ? " dice-table-spectacle--compact" : ""}`}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <div className="dice-table-spectacle__curtain" aria-hidden="true" />
      <div className="dice-table-spectacle__frame">
        <header className="dice-table-spectacle__header">
          <VipChip label="VIP" pulse className="dice-table-spectacle__chip" />
          <p className="dice-table-spectacle__tier">PRIVATE TABLE · HIGH LIMIT</p>
          <p className="dice-table-spectacle__actor">{actorUsername}</p>
          <p className="dice-table-spectacle__phase">
            {phaseLabel ||
              (rolling ? "кубики на сукне" : "бросок завершён")}
          </p>
          {subtitle && (
            <p className="dice-table-spectacle__sub muted">{subtitle}</p>
          )}
        </header>

        {indefiniteRoll ? (
          <div className="dice-felt-waiting">
            <div className="dice-felt-waiting__inner">
              <span className="dice-felt-waiting__pulse" />
              <p>Кубики летят на сукно…</p>
            </div>
          </div>
        ) : (
          <PhysicsDiceScene
            key={`dice-roll-${rollKey}-${rolling ? "live" : "frozen"}`}
            diceCount={count}
            finalValues={rolling ? null : showValues}
            frozen={!rolling}
            active={rolling}
            onAllSettled={handlePhysicsSettled}
          />
        )}

        {phase === "result" && displayValues && (
          <p className="dice-physics-sum">
            Выпало: <strong>{displayValues.join(" + ")}</strong>
            {" = "}
            <strong>{displayValues.reduce((a, b) => a + b, 0)}</strong>
          </p>
        )}

        {phase === "result" && children}

        {phase === "result" && requireAccept && (
          <button
            type="button"
            className="btn primary dice-table-accept"
            onClick={() => onDone?.()}
          >
            Принять бросок
          </button>
        )}
      </div>
    </motion.div>
  );
}
