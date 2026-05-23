export default function CommentOverlay({ state }) {
  if (!state?.text) return null;
  return (
    <div className="ai-roast-overlay" aria-live="polite">
      <div className="ai-roast-bubble">
        <p className="ai-roast-label">
          Комментатор
          {state.targetPlayer ? ` · ${state.targetPlayer}` : ""}
        </p>
        <p className="ai-roast-text">{state.text}</p>
      </div>
    </div>
  );
}
