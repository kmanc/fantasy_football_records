import managerBios from "../../../public/static/meet_the_managers/manager_bios.json";
import type { RenderContext } from "../context";
import { escapeHtml } from "../html";
import { renderPage } from "../layout";

const bios: Record<string, string> = managerBios;

export function renderMeetTheManagers(ctx: RenderContext): string {
  const managers = [...ctx.league.membersList()]
    .filter((member) => member.leftYear === ctx.league.activeYear)
    .map((member) => member.name)
    .sort()
    .map((name) => ({ displayName: name, keyName: name.toLowerCase().replaceAll(" ", "") }));

  const cardsHtml = managers
    .map((manager) => {
      const src = `/static/meet_the_managers/${manager.keyName}.jpg`;
      const fallback = "/static/meet_the_managers/default_manager.jpg";
      return `<div class="manager-card">
    <img alt="${escapeHtml(manager.displayName)}" src="${src}" onerror="this.onerror=null;this.src='${fallback}';">
    <h4>${escapeHtml(manager.displayName)}</h4>
    <p>${escapeHtml(bios[manager.keyName] ?? "")}</p>
</div>`;
    })
    .join("\n");

  const content = `<div class="managers-grid">
${cardsHtml}
</div>`;

  return renderPage({
    titlePrefix: ctx.titlePrefix,
    recordName: "Meet the members",
    currentPath: "/meet_the_managers",
    members: ctx.members,
    content,
    extraHeadLinks: ["/static/meet_the_managers.css"],
  });
}
