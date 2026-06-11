/** Очки в стиле фишки казино (вместо молнии). */
export default function CasinoPoints({ value, prefix = "+" }) {
  if (value == null || value === "") return null;
  return (
    <span className="casino-points">
      {prefix}
      {value}
      <span className="casino-points__chip" aria-hidden="true">
        ♦
      </span>
    </span>
  );
}
