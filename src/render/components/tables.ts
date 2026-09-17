import { escapeHtml } from "../html";

export interface TableColumn {
  label: string;
  numeric?: boolean;
  /** Marks columns that need special treatment: display-font name columns, or the rank badge column. */
  kind?: "member" | "team" | "rank";
}

export interface TableCell {
  content: string;
  numeric?: boolean;
}

/** Renders a leaderboard table. Each row is zipped against `columns` so every <td> carries a
 * `data-label` for the mobile stacked-card layout (see tables.css). */
export function renderTable(columns: TableColumn[], rows: TableCell[][]): string {
  const headHtml = columns
    .map((c) => `<th${c.numeric ? ' class="numeric"' : ""}>${escapeHtml(c.label)}</th>`)
    .join("\n        ");

  const bodyHtml = rows
    .map((row) => {
      const cellsHtml = row
        .map((cell, i) => {
          const column = columns[i];
          if (!column) return "";
          const classes = [
            cell.numeric ? "numeric" : "",
            column.kind === "member" ? "col-member" : "",
            column.kind === "team" ? "col-team" : "",
            column.kind === "rank" ? "col-rank" : "",
          ]
            .filter(Boolean)
            .join(" ");
          return `<td data-label="${escapeHtml(column.label)}"${classes ? ` class="${classes}"` : ""}>${cell.content}</td>`;
        })
        .join("\n");
      return `<tr>\n${cellsHtml}\n</tr>`;
    })
    .join("\n    ");

  return `<div class="table-wrap">
    <table class="record-table">
        <thead>
        <tr>
            ${headHtml}
        </tr>
        </thead>
        <tbody>
        ${bodyHtml}
        </tbody>
    </table>
</div>`;
}

const RANK_TIER = ["gold", "silver", "bronze"] as const;

/** A `#` rank cell for leaderboard tables, with a medal treatment for the top 3. */
export function rankCell(rank: number): TableCell {
  const tier = RANK_TIER[rank - 1];
  const tierClass = tier ? ` ${tier}` : "";
  return { content: `<span class="rank-badge${tierClass}">${rank}</span>`, numeric: false };
}

export const RANK_COLUMN: TableColumn = { label: "#", kind: "rank" };

export function cell(content: string, numeric = false): TableCell {
  return { content, numeric };
}
