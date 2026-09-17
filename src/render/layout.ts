import { escapeHtml } from "./html";

interface NavItem {
  name: string;
  url: string;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    label: "All-time records",
    items: [
      { name: "Championships", url: "/championships" },
      { name: "Win percent", url: "/win_percent" },
      { name: "Playoff appearances", url: "/playoff_appearances" },
    ],
  },
  {
    label: "Season records",
    items: [
      { name: "All-time regular season points", url: "/total_regular_season_points" },
      { name: "All-time playoff points", url: "/total_playoff_points" },
      { name: "Highest season points", url: "/highest_regular_season" },
      { name: "Lowest season points", url: "/lowest_regular_season" },
      { name: "Best defense", url: "/best_defense" },
      { name: "Worst defense", url: "/worst_defense" },
    ],
  },
  {
    label: "Weekly records",
    items: [
      { name: "Highest week points", url: "/highest_week" },
      { name: "Lowest week points", url: "/lowest_week" },
      { name: "Highest week loss", url: "/highest_loss" },
      { name: "Lowest week win", url: "/lowest_win" },
    ],
  },
];

function renderNavbar(titlePrefix: string, members: string[], currentPath: string): string {
  const groupsHtml = NAV_GROUPS.map((group, index) => {
    const groupActive = group.items.some((item) => item.url === currentPath);
    const itemsHtml = group.items
      .map(
        (item) => `<li>
    <a class="${currentPath === item.url ? "current-path" : ""}" href="${item.url}">${escapeHtml(item.name)}</a>
</li>`,
      )
      .join("\n");
    return `<li class="has-dropdown">
    <details${groupActive ? " open" : ""}>
        <summary>${escapeHtml(group.label)}</summary>
        <ul class="dropdown-menu">
            ${itemsHtml}
        </ul>
    </details>
</li>`;
  }).join("\n");

  const onH2hPage = currentPath.startsWith("/head-to-head/");
  const h2hItemsHtml = members
    .map(
      (member) => `<li>
    <a class="${currentPath === `/head-to-head/${member}` ? "current-path" : ""}" href="/head-to-head/${encodeURIComponent(member)}">${escapeHtml(member)}</a>
</li>`,
    )
    .join("\n");

  return `<header class="site-header">
    <div class="site-header-bar">
        <a class="brand" href="/">${escapeHtml(titlePrefix || "Records")}</a>
        <input type="checkbox" id="nav-toggle" class="nav-toggle-input">
        <label for="nav-toggle" class="nav-toggle-btn" aria-label="Toggle navigation">
            <span class="bars"><span></span><span></span><span></span></span>
        </label>
        <nav class="site-nav" aria-label="Primary">
            <ul>
                <li><a class="${currentPath === "/snapshot" ? "current-path" : ""}" href="/snapshot">Standings</a></li>

                ${groupsHtml}

                <li><a class="${currentPath === "/meet_the_managers" ? "current-path" : ""}" href="/meet_the_managers">Meet the managers</a></li>

                <li class="has-dropdown">
                    <details${onH2hPage ? " open" : ""}>
                        <summary>Head-to-head</summary>
                        <ul class="dropdown-menu">
                            ${h2hItemsHtml}
                        </ul>
                    </details>
                </li>
            </ul>
        </nav>
    </div>
</header>`;
}

/** Native <details> don't close on an outside click; this closes any open nav dropdown when
 * the user clicks elsewhere or hits Escape. The nav is fully usable without it. */
const NAV_CLOSE_SCRIPT = `<script>
document.addEventListener("click", function (event) {
    document.querySelectorAll(".site-nav details[open]").forEach(function (details) {
        if (!details.contains(event.target)) details.removeAttribute("open");
    });
});
document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") return;
    document.querySelectorAll(".site-nav details[open]").forEach(function (details) {
        details.removeAttribute("open");
    });
});
</script>`;

export interface PageChrome {
  titlePrefix: string;
  recordName: string;
  currentPath: string;
  members: string[];
  content: string;
  /** Set false when `content` supplies its own <h1>/hero (home, snapshot) instead of the shared page-head. */
  heading?: boolean;
  extraHeadLinks?: string[];
}

export function renderPage(chrome: PageChrome): string {
  const extraLinks = (chrome.extraHeadLinks ?? []).map((href) => `<link href="${href}" rel="stylesheet">`).join("\n");
  const showHeading = chrome.heading ?? true;
  // Pages with a custom hero (heading: false) own their own <h1> and .wrap sections, so a
  // snapshot-style hero band can run full-bleed edge to edge above the constrained content.
  const body = showHeading
    ? `<div class="wrap page-head">
                <h1>${escapeHtml(chrome.recordName)}</h1>
            </div>
            <div class="wrap">
                ${chrome.content}
            </div>`
    : chrome.content;

  return `<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="icon" type="image/svg+xml" href="/favicon.svg">
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Oswald:wght@500;600;700&display=swap" rel="stylesheet">
        <link href="/static/base.css" rel="stylesheet">
        <link href="/static/navbar.css" rel="stylesheet">
        <link href="/static/tables.css" rel="stylesheet">
        <title>${escapeHtml(chrome.titlePrefix)}: ${escapeHtml(chrome.recordName)}</title>
        ${extraLinks}
    </head>
    <body>
        ${renderNavbar(chrome.titlePrefix, chrome.members, chrome.currentPath)}

        <main class="content">
            ${body}
        </main>

        ${NAV_CLOSE_SCRIPT}
    </body>
</html>`;
}
