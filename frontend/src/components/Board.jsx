import { useEffect, useState } from "react";
import { playerName } from "../playerName";
import {
  cellGridPosition,
  cellColor,
  cellImageCandidates,
  isSpecialCellArt,
  tokenSizeFraction,
} from "../boardLayout";

function BoardCell({ cell, tokens, hovered, onHover }) {
  const pos = cellGridPosition(cell.id);
  const candidates = cellImageCandidates(cell);
  const specialArt = isSpecialCellArt(cell);
  const [candidateIndex, setCandidateIndex] = useState(0);
  const [imageOk, setImageOk] = useState(true);
  const imageUrl = candidates[candidateIndex] || null;
  const showImage = imageUrl && imageOk;
  const tokenFrac = tokenSizeFraction(tokens.length);

  useEffect(() => {
    setCandidateIndex(0);
    setImageOk(true);
  }, [cell.id, candidates.join("|")]);

  return (
    <div
      className={[
        "board-cell",
        pos.corner ? "corner" : "edge",
        pos.corner ? `corner-${cell.id}` : "",
        pos.edge || "",
        hovered ? "hovered" : "",
        showImage ? "has-image" : "",
        showImage && specialArt ? "has-cell-art" : "",
        showImage && !specialArt ? "has-logo-art" : "",
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
      {imageUrl && (
        <img
          key={imageUrl}
          src={imageUrl}
          alt=""
          className="cell-bg"
          onLoad={() => setImageOk(true)}
          onError={() => {
            if (candidateIndex + 1 < candidates.length) {
              setImageOk(true);
              setCandidateIndex((i) => i + 1);
            } else {
              setImageOk(false);
            }
          }}
          style={{ display: showImage ? "block" : "none" }}
        />
      )}
      {!showImage && <span className="cell-name">{cell.name}</span>}
      <div className="cell-tokens" style={{ "--token-frac": tokenFrac }}>
        {tokens.map((p) => (
          <img
            key={p.id}
            src={p.avatarUrl}
            alt={playerName(p)}
            title={playerName(p)}
            className="token"
          />
        ))}
      </div>
    </div>
  );
}

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
      <div className="board-grid" role="img" aria-label="Игровое поле DOTAG 3">
        <div className="board-center" aria-hidden="true">
          <div className="board-plasma">
            <div className="board-plasma__bezel">
              <div className="board-plasma__screen">
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
                <div className="board-plasma__fx" aria-hidden="true">
                  <div className="board-plasma__overlay" />
                  <div className="board-plasma__shine" />
                  <div className="board-plasma__scan" />
                  <div className="board-plasma__watermark">PREMIUM FLOOR</div>
                </div>
                <div className="board-plasma__hud-bar board-plasma__hud-bar--top">
                  <span className="board-plasma__hud board-plasma__hud--live">● LIVE</span>
                  <span className="board-plasma__hud">VIP SLOTS</span>
                </div>
                <div className="board-plasma__hud-bar board-plasma__hud-bar--bottom">
                  <span className="board-plasma__hud">HIGH LIMIT</span>
                  <span className="board-plasma__hud">♛ DOTAG TV ♛</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        {cells.map((cell) => {
          const tokens = byPos[cell.id] || [];
          return (
            <BoardCell
              key={cell.id}
              cell={cell}
              tokens={tokens}
              hovered={hoverCell?.id === cell.id}
              onHover={onHover}
            />
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
