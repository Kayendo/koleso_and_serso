import {
  cellGridPosition,
  cellColor,
  logoUrl,
  tokenSizeFraction,
} from "../boardLayout";

export default function Board({
  cells,
  players,
  hoverCell,
  onHover,
  flyingToken,
  centerGif,
}) {
  const byPos = {};
  const flyingId = flyingToken?.userId;
  players.forEach((p) => {
    if (p.id === flyingId) return;
    if (!byPos[p.position]) byPos[p.position] = [];
    byPos[p.position].push(p);
  });

  return (
    <div className="board-wrap">
      <div className="board-grid">
        <div className="board-center" aria-hidden="true">
          {centerGif?.url ? (
            <img
              key={centerGif.url}
              src={centerGif.url}
              alt={centerGif.title || "meme"}
              className="board-center-gif"
            />
          ) : (
            <span className="board-center-placeholder">meme</span>
          )}
        </div>
        {cells.map((cell) => {
          const pos = cellGridPosition(cell.id);
          const tokens = byPos[cell.id] || [];
          const logo = logoUrl(cell);
          const tokenFrac = tokenSizeFraction(tokens.length);
          return (
            <div
              key={cell.id}
              className={[
                "board-cell",
                pos.corner ? "corner" : "edge",
                pos.edge || "",
                hoverCell?.id === cell.id ? "hovered" : "",
              ]
                .filter(Boolean)
                .join(" ")}
              style={{
                gridRow: pos.row,
                gridColumn: pos.col,
                backgroundColor: cellColor(cell),
              }}
              onMouseEnter={() => onHover(cell)}
              onMouseLeave={() => onHover(null)}
            >
              {logo ? (
                <img
                  src={logo}
                  alt=""
                  className="cell-logo"
                  onError={(e) => {
                    e.target.style.display = "none";
                  }}
                />
              ) : (
                <span className="cell-name">{cell.name}</span>
              )}
              <div
                className="cell-tokens"
                style={{ "--token-frac": tokenFrac }}
              >
                {tokens.map((p) => (
                  <img
                    key={p.id}
                    src={p.avatarUrl}
                    alt={p.username}
                    title={p.username}
                    className="token"
                  />
                ))}
              </div>
            </div>
          );
        })}
        {flyingToken && (
          <img
            src={flyingToken.avatarUrl}
            alt=""
            className="token-flying"
            style={{
              left: `${flyingToken.left}%`,
              top: `${flyingToken.top}%`,
            }}
          />
        )}
      </div>
    </div>
  );
}
