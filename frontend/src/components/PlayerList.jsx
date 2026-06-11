import { motion } from "framer-motion";
import { playerName } from "../playerName";
import { rankClass, rankTitle, RANK_TITLES } from "../playerRanks";
import CasinoPoints from "../ui/CasinoPoints";
import VipChip from "../ui/VipChip";
import VipLoungeStrip from "../ui/VipLoungeStrip";

function statusLabel(p) {
  if (p.turnPhase === "playing") return "В игре";
  if (p.inDurka) return "Дурка";
  return "На поле";
}

export default function PlayerList({ players, currentUser, onSelect }) {
  const sorted = [...players].sort((a, b) => b.points - a.points);

  return (
    <aside className="sidebar right sidebar--vip">
      <VipLoungeStrip items={["LEADERBOARD", "HIGH ROLLERS", "WHALE WATCH", "BLACK CARD", "TOP TIER"]} />
      <div className="sidebar-brand sidebar-brand--vip">
        <div className="sidebar-brand__mark sidebar-brand__mark--emerald" aria-hidden="true">
          ♦
        </div>
        <div>
          <VipChip label="ELITE" variant="emerald" className="sidebar-vip-chip" />
          <h2>Игроки</h2>
        </div>
      </div>
      <p className="sidebar-time sidebar-time--vip">
        <span className="sidebar-live-dot" />
        {sorted.length} high rollers at the table
      </p>

      <ul className="player-list">
        {sorted.map((p, i) => (
          <motion.li
            key={p.id}
            className={currentUser?.id === p.id ? "active" : ""}
            onClick={() => onSelect(p)}
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05, duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
            whileHover={{ x: -4 }}
            whileTap={{ scale: 0.98 }}
          >
            <span
              className={rankClass(i)}
              title={RANK_TITLES[i]?.hint}
            >
              {i + 1}
            </span>
            <div className="player-avatar-wrap">
              <img src={p.avatarUrl} alt="" className="avatar-sm" />
              {i < RANK_TITLES.length && (
                <span
                  className={`player-vip-tag player-vip-tag--${i + 1}`}
                  title={RANK_TITLES[i].hint}
                >
                  {rankTitle(i)}
                </span>
              )}
            </div>
            <div className="player-meta">
              <span className="name">{playerName(p)}</span>
              <span className="status">{statusLabel(p)}</span>
            </div>
            <div className="player-score player-score--chips">
              <CasinoPoints value={p.points} prefix="" />
            </div>
          </motion.li>
        ))}
      </ul>
    </aside>
  );
}
