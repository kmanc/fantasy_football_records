/** Jinja2 auto-escapes by default; this replaces that safety net for the hand-rolled templates. */
export function escapeHtml(value: string | number): string {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

/** Whole-number counts (championships, playoff appearances): comma-grouped, no decimal point. */
export function formatCount(value: number): string {
  return value.toLocaleString("en-US", { maximumFractionDigits: 0 });
}

/**
 * Points/percentage values: comma-grouped, always at least one decimal digit (matches Python,
 * where these values are floats and `"{:,}".format()`/`str()` always show a decimal point).
 */
export function formatPoints(value: number): string {
  return value.toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 2 });
}
