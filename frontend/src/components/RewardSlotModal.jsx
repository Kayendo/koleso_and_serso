import { useCallback, useRef, useState } from "react";
import { motion } from "framer-motion";
import { apiPost } from "../api";
import VipChip from "../ui/VipChip";

const DRUM_VALUES = [1, 2, 3];
const SEGMENT_H = 120;

function wheelsLabel(n) {
  if (n === 1) return "1 призовое колесо";
  if (n >= 2 && n <= 4) return `${n} призовых колеса`;
  return `${n} призовых колёс`;
}

export default function RewardSlotModal({ actorUsername, onComplete, onError }) {
  const [leverPulled, setLeverPulled] = useState(false);
  const [spinning, setSpinning] = useState(false);
  const [result, setResult] = useState(null);
  const [offset, setOffset] = useState(0);
  const offsetRef = useRef(0);
  const animRef = useRef(null);

  const spinTo = useCallback((value, onEnd) => {
    const idx = DRUM_VALUES.indexOf(value);
    if (idx < 0) return;
    const extraLoops = 5 + Math.floor(Math.random() * 3);
    const target = -(extraLoops * DRUM_VALUES.length + idx) * SEGMENT_H;
    const start = offsetRef.current;
    const duration = 2800 + Math.random() * 600;
    const t0 = performance.now();

    const tick = (now) => {
      const t = Math.min(1, (now - t0) / duration);
      const eased = 1 - Math.pow(1 - t, 3.5);
      const next = start + (target - start) * eased;
      offsetRef.current = next;
      setOffset(next);
      if (t < 1) {
        animRef.current = requestAnimationFrame(tick);
      } else {
        offsetRef.current = target;
        setOffset(target);
        setSpinning(false);
        onEnd?.();
      }
    };
    animRef.current = requestAnimationFrame(tick);
  }, []);

  const pullLever = async () => {
    if (leverPulled || spinning || result != null) return;
    setLeverPulled(true);
    setTimeout(() => setLeverPulled(false), 520);

    setSpinning(true);
    try {
      const data = await apiPost("/turn/roll-reward-dice", {});
      const value = Math.min(3, Math.max(1, data.rewardDice?.[0] ?? data.rewardItemSpins ?? 1));
      spinTo(value, () => {
        setResult({ value, data });
        setTimeout(() => onComplete?.(data), 2200);
      });
    } catch (ex) {
      setSpinning(false);
      onError?.(ex.message);
    }
  };

  const strip = [];
  for (let loop = 0; loop < 12; loop += 1) {
    DRUM_VALUES.forEach((v) => strip.push(v));
  }

  return (
    <motion.div
      className="overlay overlay-spectate overlay--casino"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <div className="reward-slot">
        <header className="reward-slot__header">
          <VipChip label="JACKPOT" variant="ruby" pulse className="reward-slot__chip" />
          <p className="reward-slot__tier">WHALE LOUNGE · PREMIUM REWARDS</p>
          <p className="reward-slot__actor">{actorUsername}</p>
          <p className="reward-slot__title">Призовые вращения</p>
          <p className="muted">Потяните ручку — барабан определит число колёс</p>
        </header>

        <div className="reward-slot__machine">
          <div className="reward-slot__body">
            <div className="reward-slot__window">
              <div
                className="reward-slot__drum"
                style={{ transform: `translateY(${offset}px)` }}
              >
                {strip.map((v, i) => (
                  <div key={i} className="reward-slot__segment">
                    <span>{v}</span>
                  </div>
                ))}
              </div>
              <div className="reward-slot__window-shine" aria-hidden="true" />
            </div>

            <button
              type="button"
              className={`reward-slot__lever${leverPulled ? " reward-slot__lever--pulled" : ""}${spinning ? " reward-slot__lever--busy" : ""}`}
              onClick={pullLever}
              disabled={spinning || result != null}
              aria-label="Потянуть ручку"
            >
              <span className="reward-slot__lever-mount">
                <span className="reward-slot__lever-shaft">
                  <span className="reward-slot__lever-knob" />
                </span>
              </span>
            </button>
          </div>
        </div>

        {result && (
          <motion.p
            className="reward-slot__result"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
          >
            Выпало <strong>{result.value}</strong> — {wheelsLabel(result.value)}
          </motion.p>
        )}
      </div>
    </motion.div>
  );
}
