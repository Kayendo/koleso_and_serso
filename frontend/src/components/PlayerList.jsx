import { playerName } from "../playerName";

export default function PlayerList({ players, currentUser, onSelect }) {
  const sorted = [...players].sort((a, b) => b.points - a.points);
  return (
    <aside className="sidebar right">
      <h2>Игроки</h2>
      <ul className="player-list">
        {sorted.map((p, i) => (
          <li
            key={p.id}
            className={currentUser?.id === p.id ? "active" : ""}
            onClick={() => onSelect(p)}
          >
            <img src={p.avatarUrl} alt="" className="avatar-sm" />
            <div className="player-meta">
              <span className="name">{playerName(p)}</span>
              <span className="status">
                {p.turnPhase === "playing"
                  ? "В игре"
                  : p.inDurka
                    ? "Дурка"
                    : "На поле"}
              </span>
            </div>
            <div className="player-score">
              <span>{p.points}⚡</span>
              <small>#{i + 1}</small>
            </div>
          </li>
        ))}
      </ul>
    </aside>
  );
}
