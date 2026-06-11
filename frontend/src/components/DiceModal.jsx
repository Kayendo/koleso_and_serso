import { motion } from "framer-motion";
import DiceTableSpectacle from "./dice/DiceTableSpectacle";

export default function DiceModal({
  dice,
  rawDice,
  actorUsername,
  factors = [],
  steps,
  label,
  showEffects = true,
  requireAccept = false,
  physicsRoll = false,
  awaitingOthersRoll = false,
  rollKey = 0,
  diceCount = 2,
  onDone,
  onPhysicsConfirmed,
}) {
  if (awaitingOthersRoll) {
    return (
      <motion.div
        className="overlay overlay-spectate overlay--casino"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        <DiceTableSpectacle
          indefiniteRoll
          actorUsername={actorUsername}
          phaseLabel={`${actorUsername} бросает кубики…`}
        />
      </motion.div>
    );
  }

  if (physicsRoll) {
    return (
      <motion.div
        className="overlay overlay-spectate overlay--casino"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
      >
        <DiceTableSpectacle
          physicsRoll
          rollKey={rollKey}
          diceCount={diceCount}
          actorUsername={actorUsername}
          requireAccept={requireAccept}
          onDone={onDone}
          onPhysicsConfirmed={onPhysicsConfirmed}
        />
      </motion.div>
    );
  }

  const faces = dice?.length ? dice : rawDice;
  if (!faces?.length) return null;

  const rawSum =
    rawDice?.length >= 2
      ? rawDice[0] + (rawDice[1] ?? 0)
      : rawDice?.[0] ?? faces[0] + (faces[1] ?? 0);
  const faceSum =
    faces.length === 1 ? faces[0] : faces[0] + (faces[1] ?? 0);
  const totalSteps = steps ?? faceSum;
  const stepsChanged = totalSteps !== faceSum;
  const rawChanged = rawDice?.length >= 2 && rawSum !== faceSum;

  return (
    <motion.div
      className="overlay overlay-spectate overlay--casino"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <DiceTableSpectacle
        finalValues={faces}
        rollKey={rollKey}
        actorUsername={actorUsername}
        requireAccept={requireAccept}
        onDone={onDone}
      >
        <motion.div
          className="dice-table-result"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
        >
          <p className="dice-sum">
            {rawChanged && rawSum !== faceSum ? (
              <>
                {rawSum} → {faceSum} → <strong>{totalSteps}</strong> клеток
              </>
            ) : stepsChanged ? (
              <>
                {faceSum} → <strong>{totalSteps}</strong> клеток
              </>
            ) : (
              <>
                <strong>{totalSteps}</strong> клеток
              </>
            )}
            {label ? ` (${label})` : ""}
          </p>
          {showEffects && (
            <div className="dice-effects-panel">
              <p className="dice-effects-title">Эффекты на этот ход</p>
              {factors.length > 0 ? (
                <ul className="dice-effects-list">
                  {factors.map((f, i) => (
                    <li key={i}>{f}</li>
                  ))}
                </ul>
              ) : (
                <p className="dice-effects-none">Без дополнительных модификаторов</p>
              )}
            </div>
          )}
        </motion.div>
      </DiceTableSpectacle>
    </motion.div>
  );
}
