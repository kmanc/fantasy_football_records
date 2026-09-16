import { escapeHtml } from "../html";

export interface TableColumn {
  label: string;
  numeric?: boolean;
}

export function renderTable(columns: TableColumn[], rows: string[]): string {
  const headHtml = columns.map((c) => `<th${c.numeric ? ' class="numeric"' : ""}>${escapeHtml(c.label)}</th>`).join("\n        ");
  return `<table class="table table-striped table-hover" id="data">
    <thead>
    <tr>
        ${headHtml}
    </tr>
    </thead>
    <tbody>
    ${rows.join("\n    ")}
    </tbody>
</table>`;
}

export function tr(cells: string[]): string {
  return `<tr>\n${cells.join("\n")}\n</tr>`;
}

export function td(content: string, numeric = false): string {
  return `<td${numeric ? ' class="numeric"' : ""}>${content}</td>`;
}
