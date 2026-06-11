export default function SceneBackground() {
  return (
    <div className="scene-bg" aria-hidden="true">
      <div className="scene-bg__mesh" />
      <div className="scene-bg__orb scene-bg__orb--gold" />
      <div className="scene-bg__orb scene-bg__orb--emerald" />
      <div className="scene-bg__orb scene-bg__orb--violet" />
      <div className="scene-bg__sparkles" />
      <div className="scene-bg__chips">
        {["♠", "♦", "♣", "♥", "◆", "✦"].map((sym, i) => (
          <span key={i} className="scene-bg__chip" style={{ "--i": i }}>
            {sym}
          </span>
        ))}
      </div>
      <div className="scene-bg__grain" />
      <div className="scene-bg__vignette" />
      <div className="scene-bg__gold-rail scene-bg__gold-rail--top" />
      <div className="scene-bg__gold-rail scene-bg__gold-rail--bottom" />
    </div>
  );
}
