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
    <a class="dropdown-item ${currentPath === item.url ? "current-path" : ""}" href="${item.url}">${escapeHtml(item.name)}</a>
</li>`,
      )
      .join("\n");
    return `<li class="nav-item dropdown">
    <a class="nav-link dropdown-toggle ${groupActive ? "current-path" : ""}" href="#" id="navbarDropdown${index + 1}"
       role="button" data-bs-toggle="dropdown" aria-expanded="false">
        ${escapeHtml(group.label)}
    </a>
    <ul class="dropdown-menu" aria-labelledby="navbarDropdown${index + 1}">
        ${itemsHtml}
    </ul>
</li>`;
  }).join("\n");

  const onH2hPage = currentPath.startsWith("/head-to-head/");
  const h2hItemsHtml = members
    .map(
      (member) => `<li>
    <a class="dropdown-item ${currentPath === `/head-to-head/${member}` ? "current-path" : ""}" href="/head-to-head/${encodeURIComponent(member)}">${escapeHtml(member)}</a>
</li>`,
    )
    .join("\n");

  return `<link href="/static/navbar.css" rel="stylesheet">
<nav class="navbar navbar-expand-lg navbar-light bg-light">
    <div class="container-fluid">
        <a class="navbar-brand" href="/">${escapeHtml(titlePrefix || "Records")}</a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav"
                aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
            <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarNav">
            <ul class="navbar-nav">
                <li class="nav-item">
                    <a class="nav-link ${currentPath === "/snapshot" ? "current-path" : ""}" href="/snapshot">Standings</a>
                </li>

                ${groupsHtml}

                <li class="nav-item">
                    <a class="nav-link ${currentPath === "/meet_the_managers" ? "current-path" : ""}" href="/meet_the_managers">Meet the managers</a>
                </li>

                <li class="nav-item dropdown">
                    <a class="nav-link dropdown-toggle ${onH2hPage ? "current-path" : ""}" href="#" id="navbarDropdownH2H"
                       role="button" data-bs-toggle="dropdown" aria-expanded="false">
                        Head-to-head
                    </a>
                    <ul class="dropdown-menu" aria-labelledby="navbarDropdownH2H">
                        ${h2hItemsHtml}
                    </ul>
                </li>
            </ul>
        </div>
    </div>
</nav>`;
}

export interface PageChrome {
  titlePrefix: string;
  recordName: string;
  currentPath: string;
  members: string[];
  content: string;
  extraHeadLinks?: string[];
}

export function renderPage(chrome: PageChrome): string {
  const extraLinks = (chrome.extraHeadLinks ?? []).map((href) => `<link href="${href}" rel="stylesheet">`).join("\n");

  return `<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="/static/base.css" rel="stylesheet">
        <link href="/static/tables.css" rel="stylesheet">
        <link crossorigin="anonymous" href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css"
              integrity="sha384-1BmE4kWBq78iYhFldvKuhfTAU6auU8tT94WrHftjDbrCEXSU1oBoqyl2QvZ6jIW3" rel="stylesheet">
        <script crossorigin="anonymous"
                integrity="sha384-ka7Sk0Gln4gmtz2MlQnikT1wXgYsOg+OMhuP+IlRH9sENBO0LRn5q+8nbTov4+1p"
                src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        <title>${escapeHtml(chrome.titlePrefix)}: ${escapeHtml(chrome.recordName)}</title>
        ${extraLinks}
    </head>
    <body>
        ${renderNavbar(chrome.titlePrefix, chrome.members, chrome.currentPath)}

        <div class="container recordname">
            <h1 align="center">${escapeHtml(chrome.recordName)}</h1>
            <hr>
        </div>

        <div class="container content">
            ${chrome.content}
        </div>

        <div class="footer">
            Updated weekly by <a href="https://github.com/kmanc/fantasy_football_records">fantasy_football_records</a>
        </div>
    </body>
</html>`;
}
