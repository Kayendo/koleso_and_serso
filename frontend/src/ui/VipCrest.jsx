/** Декоративный герб над модалками и столами. */
export default function VipCrest({ subtitle }) {
  return (
    <div className="vip-crest" aria-hidden="true">
      <div className="vip-crest__wings">✦</div>
      <div className="vip-crest__crown">♛</div>
      {subtitle && <p className="vip-crest__sub">{subtitle}</p>}
    </div>
  );
}
