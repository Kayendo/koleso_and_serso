import { motion } from "framer-motion";
import DiceTableSpectacle from "./dice/DiceTableSpectacle";

const RESULT_MS = 2800;

export default function RewardDiceModal({ dice, actorUsername, onDone }) {
  const value = Math.min(6, Math.max(1, dice?.[0] ?? 1));

  const wheelsLabel =
    value === 1 ? "1 колесо предметов" : `${value} колеса предметов`;

  return (
    <motion.div
      className="overlay overlay-spectate overlay--casino"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      <DiceTableSpectacle
        finalValues={[value]}
        actorUsername={actorUsername}
        subtitle="Призовой кубик · награда за прохождение"
        phaseLabel="призовой бросок"
        onRollComplete={() => setTimeout(() => onDone?.(), RESULT_MS)}
      >
        <div className="dice-table-result reward-dice-result">
          <p className="reward-dice-prize">
            Выпало <strong>{value}</strong>
          </p>
          <p className="muted">{wheelsLabel}</p>
        </div>
      </DiceTableSpectacle>
    </motion.div>
  );
}
