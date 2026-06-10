import { genreButtonLabel } from "../genres";

export default function GenrePicker({
  genres,
  value,
  onChange,
  disabled = false,
  layout = "column",
}) {
  if (!genres?.length) return null;
  const gridClass =
    layout === "grid" ? "genre-grid genre-picker-grid" : "admin-genre-grid";

  return (
    <div className={gridClass}>
      {genres.map((g) => (
        <button
          key={g.id}
          type="button"
          className={`btn full ${String(value) === String(g.id) ? "primary" : ""}`}
          onClick={() => onChange(g.id)}
          disabled={disabled}
          title={g.label || genreButtonLabel(g)}
        >
          {genreButtonLabel(g)}
        </button>
      ))}
    </div>
  );
}
