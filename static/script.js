let websites = [];
let websiteChecks = {};
let websiteAnalytics = {};
let websiteIncidents = {};
let editingWebsiteId = null;
let selectedAnalysisWebsiteId = null;
let currentAnalysis = null;


document.addEventListener(
    "DOMContentLoaded",
    function () {
        setupEventListeners();
        loadDashboard();
    }
);


function setupEventListeners() {
    const addButton = document.getElementById(
        "addWebsiteButton"
    );

    const refreshButton = document.getElementById(
        "refreshDashboardButton"
    );

    const closeButton = document.getElementById(
        "closeWebsiteModalButton"
    );

    const cancelButton = document.getElementById(
        "cancelWebsiteButton"
    );

    const form = document.getElementById(
        "websiteForm"
    );

    const historySelector = document.getElementById(
        "historyWebsiteSelect"
    );

    const analysisSelector = document.getElementById(
        "analysisWebsiteSelect"
    );

    const analyzeButton = document.getElementById(
        "analyzeWebsiteButton"
    );

    if (addButton) {
        addButton.addEventListener(
            "click",
            function () {
                openAddWebsiteModal();
            }
        );
    }

    if (refreshButton) {
        refreshButton.addEventListener(
            "click",
            function () {
                loadDashboard();
            }
        );
    }

    if (closeButton) {
        closeButton.addEventListener(
            "click",
            closeWebsiteModal
        );
    }

    if (cancelButton) {
        cancelButton.addEventListener(
            "click",
            closeWebsiteModal
        );
    }

    if (form) {
        form.addEventListener(
            "submit",
            saveWebsite
        );
    }

    if (historySelector) {
        historySelector.addEventListener(
            "change",
            handleHistoryWebsiteChange
        );
    }

    if (analysisSelector) {
        analysisSelector.addEventListener(
            "change",
            handleAnalysisWebsiteChange
        );
    }

    if (analyzeButton) {
        analyzeButton.addEventListener(
            "click",
            analyzeSelectedWebsite
        );
    }
}


async function loadDashboard() {
    try {
        const response = await fetch(
            "/api/websites"
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.error ||
                "Unable to load websites."
            );
        }

        websites = data.websites || [];

        websiteChecks = {};
        websiteAnalytics = {};
        websiteIncidents = {};

        for (const website of websites) {
            await loadWebsiteChecks(
                website.id
            );

            await loadWebsiteAnalytics(
                website.id
            );

            await loadWebsiteIncidents(
                website.id
            );
        }

        renderDashboard();
        renderIncidents();
        renderActivity();
        populateHistorySelector();
        populateAnalysisSelector();

    } catch (error) {
        showDashboardError(
            error.message
        );
    }
}


async function loadWebsiteChecks(
    websiteId
) {
    try {
        const response = await fetch(
            "/api/websites/" +
            websiteId +
            "/checks"
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.error ||
                "Unable to load monitoring history."
            );
        }

        websiteChecks[websiteId] =
            data.checks || [];

    } catch (error) {
        websiteChecks[websiteId] = [];
    }
}


async function loadWebsiteAnalytics(
    websiteId
) {
    try {
        const response = await fetch(
            "/api/websites/" +
            websiteId +
            "/analytics"
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.error ||
                "Unable to load analytics."
            );
        }

        websiteAnalytics[websiteId] =
            data.analytics || {};

    } catch (error) {
        websiteAnalytics[websiteId] = {};
    }
}


async function loadWebsiteIncidents(
    websiteId
) {
    try {
        const response = await fetch(
            "/api/websites/" +
            websiteId +
            "/incidents"
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.error ||
                "Unable to load incidents."
            );
        }

        websiteIncidents[websiteId] =
            data.incidents || [];

    } catch (error) {
        websiteIncidents[websiteId] = [];
    }
}


function renderDashboard() {
    updateStatistics();
    renderWebsites();
}


function updateStatistics() {
    const totalElement =
        document.getElementById(
            "totalWebsites"
        );

    const upElement =
        document.getElementById(
            "upWebsites"
        );

    const downElement =
        document.getElementById(
            "downWebsites"
        );

    const averageElement =
        document.getElementById(
            "averageResponse"
        );

    let upCount = 0;
    let downCount = 0;

    let responseValues = [];

    websites.forEach(
        function (website) {
            const checks =
                websiteChecks[website.id] ||
                [];

            if (checks.length === 0) {
                downCount += 1;
                return;
            }

            const latestCheck =
                checks[0];

            if (latestCheck.isUp) {
                upCount += 1;
            } else {
                downCount += 1;
            }

            if (
                typeof latestCheck.responseTime ===
                "number"
            ) {
                responseValues.push(
                    latestCheck.responseTime
                );
            }
        }
    );

    const average =
        responseValues.length
            ? responseValues.reduce(
                function (
                    total,
                    value
                ) {
                    return total + value;
                },
                0
            ) / responseValues.length
            : 0;

    if (totalElement) {
        totalElement.textContent =
            websites.length;
    }

    if (upElement) {
        upElement.textContent =
            upCount;
    }

    if (downElement) {
        downElement.textContent =
            downCount;
    }

    if (averageElement) {
        averageElement.textContent =
            formatResponseTime(
                average
            );
    }
}


function renderWebsites() {
    const grid =
        document.getElementById(
            "websiteGrid"
        );

    if (!grid) {
        return;
    }

    if (websites.length === 0) {
        grid.innerHTML = `
            <div class="empty-state">
                <i class="fa-solid fa-globe"></i>
                <h3>No websites monitored yet</h3>
                <p>Add your first website to start monitoring.</p>
            </div>
        `;

        return;
    }

    grid.innerHTML =
        websites.map(
            function (website) {
                const checks =
                    websiteChecks[
                        website.id
                    ] || [];

                const analytics =
                    websiteAnalytics[
                        website.id
                    ] || {};

                const latestCheck =
                    checks.length
                        ? checks[0]
                        : null;

                const isUp =
                    latestCheck
                        ? latestCheck.isUp
                        : false;

                const statusText =
                    latestCheck
                        ? (
                            isUp
                                ? "Operational"
                                : "Down"
                        )
                        : "Not Checked";

                const response =
                    latestCheck &&
                    typeof latestCheck.responseTime ===
                    "number"
                        ? formatResponseTime(
                            latestCheck.responseTime
                        )
                        : "—";

                const healthScore =
                    analytics.healthScore ??
                    "—";

                const uptime =
                    analytics.uptimePercentage !==
                    undefined
                        ? analytics.uptimePercentage +
                          "%"
                        : "—";

                return `
                    <article class="website-card">

                        <div class="website-card-header">

                            <div class="website-identity">

                                <div class="website-icon">
                                    <i class="fa-solid fa-globe"></i>
                                </div>

                                <div>

                                    <h3>
                                        ${escapeHtml(
                                            website.name
                                        )}
                                    </h3>

                                    <a
                                        href="${escapeHtml(
                                            website.url
                                        )}"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                    >
                                        ${escapeHtml(
                                            website.url
                                        )}
                                    </a>

                                </div>

                            </div>

                            <span
                                class="status-badge ${
                                    isUp
                                        ? "status-up"
                                        : "status-down"
                                }"
                            >
                                <span class="status-dot"></span>
                                ${statusText}
                            </span>

                        </div>

                        <div class="website-metrics">

                            <div class="website-metric">

                                <span>
                                    Health Score
                                </span>

                                <strong>
                                    ${healthScore}
                                </strong>

                            </div>

                            <div class="website-metric">

                                <span>
                                    Uptime
                                </span>

                                <strong>
                                    ${uptime}
                                </strong>

                            </div>

                            <div class="website-metric">

                                <span>
                                    Response
                                </span>

                                <strong>
                                    ${response}
                                </strong>

                            </div>

                        </div>

                        <div class="website-actions">

                            <button
                                class="check-button"
                                type="button"
                                data-action="check"
                                data-id="${website.id}"
                            >
                                <i class="fa-solid fa-bolt"></i>
                                Check
                            </button>

                            <button
                                class="check-button"
                                type="button"
                                data-action="history"
                                data-id="${website.id}"
                            >
                                <i class="fa-solid fa-chart-line"></i>
                                History
                            </button>

                            <button
                                class="check-button"
                                type="button"
                                data-action="analyze"
                                data-id="${website.id}"
                            >
                                <i class="fa-solid fa-magnifying-glass-chart"></i>
                                Analyze
                            </button>

                            <button
                                class="check-button"
                                type="button"
                                data-action="edit"
                                data-id="${website.id}"
                            >
                                <i class="fa-solid fa-pen"></i>
                                Edit
                            </button>

                            <button
                                class="check-button danger-button"
                                type="button"
                                data-action="delete"
                                data-id="${website.id}"
                            >
                                <i class="fa-solid fa-trash"></i>
                                Delete
                            </button>

                        </div>

                    </article>
                `;
            }
        ).join("");

    setupWebsiteCardButtons();
}


function setupWebsiteCardButtons() {
    const buttons =
        document.querySelectorAll(
            ".website-actions button"
        );

    buttons.forEach(
        function (button) {
            button.addEventListener(
                "click",
                function () {
                    const action =
                        button.dataset.action;

                    const websiteId =
                        Number(
                            button.dataset.id
                        );

                    if (action === "check") {
                        runCheck(
                            websiteId
                        );
                    }

                    if (action === "history") {
                        selectHistoryWebsite(
                            websiteId
                        );
                    }

                    if (action === "analyze") {
                        selectAnalysisWebsite(
                            websiteId
                        );
                    }

                    if (action === "edit") {
                        openEditWebsiteModal(
                            websiteId
                        );
                    }

                    if (action === "delete") {
                        deleteWebsite(
                            websiteId
                        );
                    }
                }
            );
        }
    );
}


function renderIncidents() {
    const openElement =
        document.getElementById(
            "openIncidentCount"
        );

    const resolvedElement =
        document.getElementById(
            "resolvedIncidentCount"
        );

    const totalElement =
        document.getElementById(
            "totalIncidentCount"
        );

    const statusElement =
        document.getElementById(
            "incidentSystemStatus"
        );

    const refreshElement =
        document.getElementById(
            "incidentRefreshTime"
        );

    const emptyState =
        document.getElementById(
            "incidentEmptyState"
        );

    const tableWrapper =
        document.getElementById(
            "incidentTableWrapper"
        );

    const tableBody =
        document.getElementById(
            "incidentTableBody"
        );

    const incidents = [];

    websites.forEach(
        function (website) {
            const websiteIncidentList =
                websiteIncidents[
                    website.id
                ] || [];

            websiteIncidentList.forEach(
                function (incident) {
                    incidents.push({
                        ...incident,
                        websiteName:
                            website.name
                    });
                }
            );
        }
    );

    incidents.sort(
        function (a, b) {
            return (
                new Date(
                    b.startedAt
                ) -
                new Date(
                    a.startedAt
                )
            );
        }
    );

    const openCount =
        incidents.filter(
            function (incident) {
                return incident.status ===
                    "OPEN";
            }
        ).length;

    const resolvedCount =
        incidents.filter(
            function (incident) {
                return incident.status ===
                    "RESOLVED";
            }
        ).length;

    if (openElement) {
        openElement.textContent =
            openCount;
    }

    if (resolvedElement) {
        resolvedElement.textContent =
            resolvedCount;
    }

    if (totalElement) {
        totalElement.textContent =
            incidents.length;
    }

    if (statusElement) {
        statusElement.textContent =
            openCount > 0
                ? "Attention Needed"
                : "Healthy";

        statusElement.className =
            openCount > 0
                ? "incident-status-danger"
                : "incident-status-healthy";
    }

    if (refreshElement) {
        refreshElement.textContent =
            "Updated " +
            new Date().toLocaleTimeString(
                [],
                {
                    hour: "2-digit",
                    minute: "2-digit"
                }
            );
    }

    if (
        incidents.length === 0
    ) {
        if (emptyState) {
            emptyState.style.display =
                "block";
        }

        if (tableWrapper) {
            tableWrapper.style.display =
                "none";
        }

        return;
    }

    if (emptyState) {
        emptyState.style.display =
            "none";
    }

    if (tableWrapper) {
        tableWrapper.style.display =
            "block";
    }

    if (!tableBody) {
        return;
    }

    tableBody.innerHTML =
        incidents
            .slice(0, 20)
            .map(
                function (incident) {
                    const isOpen =
                        incident.status ===
                        "OPEN";

                    return `
                        <tr>

                            <td>
                                <div class="incident-website-cell">

                                    <div class="incident-website-icon">
                                        <i class="fa-solid fa-globe"></i>
                                    </div>

                                    <strong>
                                        ${escapeHtml(
                                            incident.websiteName
                                        )}
                                    </strong>

                                </div>
                            </td>

                            <td>
                                <span
                                    class="incident-status-badge ${
                                        isOpen
                                            ? "incident-status-open"
                                            : "incident-status-resolved"
                                    }"
                                >
                                    <span class="incident-status-dot"></span>
                                    ${
                                        isOpen
                                            ? "OPEN"
                                            : "RESOLVED"
                                    }
                                </span>
                            </td>

                            <td>
                                <span class="incident-reason">
                                    ${escapeHtml(
                                        shortenText(
                                            incident.reason ||
                                            "Unknown issue",
                                            55
                                        )
                                    )}
                                </span>
                            </td>

                            <td>
                                ${formatDate(
                                    incident.startedAt
                                )}
                            </td>

                            <td>
                                ${
                                    incident.resolvedAt
                                        ? formatDate(
                                            incident.resolvedAt
                                        )
                                        : "Still active"
                                }
                            </td>

                            <td>
                                ${formatIncidentDuration(
                                    incident.startedAt,
                                    incident.resolvedAt
                                )}
                            </td>

                        </tr>
                    `;
                }
            )
            .join("");
}


function formatIncidentDuration(
    startedAt,
    resolvedAt
) {
    if (!startedAt) {
        return "—";
    }

    const start =
        new Date(
            startedAt
        ).getTime();

    const end =
        resolvedAt
            ? new Date(
                resolvedAt
            ).getTime()
            : Date.now();

    if (
        !Number.isFinite(start) ||
        !Number.isFinite(end) ||
        end < start
    ) {
        return "—";
    }

    const totalSeconds =
        Math.floor(
            (end - start) / 1000
        );

    const days =
        Math.floor(
            totalSeconds / 86400
        );

    const hours =
        Math.floor(
            (totalSeconds % 86400) / 3600
        );

    const minutes =
        Math.floor(
            (totalSeconds % 3600) / 60
        );

    const seconds =
        totalSeconds % 60;

    if (days > 0) {
        return (
            days +
            "d " +
            hours +
            "h"
        );
    }

    if (hours > 0) {
        return (
            hours +
            "h " +
            minutes +
            "m"
        );
    }

    if (minutes > 0) {
        return (
            minutes +
            "m " +
            seconds +
            "s"
        );
    }

    return (
        seconds +
        "s"
    );
}


function populateHistorySelector() {
    const selector =
        document.getElementById(
            "historyWebsiteSelect"
        );

    if (!selector) {
        return;
    }

    selector.innerHTML = `
        <option value="">
            Select a website
        </option>
    `;

    websites.forEach(
        function (website) {
            const option =
                document.createElement(
                    "option"
                );

            option.value =
                website.id;

            option.textContent =
                website.name;

            selector.appendChild(
                option
            );
        }
    );
}


function populateAnalysisSelector() {
    const selector =
        document.getElementById(
            "analysisWebsiteSelect"
        );

    if (!selector) {
        return;
    }

    selector.innerHTML = `
        <option value="">
            Select a website
        </option>
    `;

    websites.forEach(
        function (website) {
            const option =
                document.createElement(
                    "option"
                );

            option.value =
                website.id;

            option.textContent =
                website.name;

            selector.appendChild(
                option
            );
        }
    );

    if (selectedAnalysisWebsiteId) {
        selector.value =
            selectedAnalysisWebsiteId;
    }
}


function handleHistoryWebsiteChange(
    event
) {
    const websiteId =
        Number(
            event.target.value
        ) || null;

    if (!websiteId) {
        clearHistoryPanel();
        return;
    }

    renderHistory(
        websiteId
    );
}


function selectHistoryWebsite(
    websiteId
) {
    const selector =
        document.getElementById(
            "historyWebsiteSelect"
        );

    if (!selector) {
        return;
    }

    selector.value =
        websiteId;

    renderHistory(
        websiteId
    );

    const historySection =
        document.querySelector(
            ".history-section"
        );

    if (historySection) {
        historySection.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    }
}


function renderHistory(
    websiteId
) {
    const checks =
        websiteChecks[
            websiteId
        ] || [];

    const analytics =
        websiteAnalytics[
            websiteId
        ] || {};

    const emptyState =
        document.getElementById(
            "historyEmptyState"
        );

    const panel =
        document.getElementById(
            "historyPanel"
        );

    if (!emptyState || !panel) {
        return;
    }

    if (checks.length === 0) {
        emptyState.style.display =
            "block";

        panel.style.display =
            "none";

        return;
    }

    emptyState.style.display =
        "none";

    panel.style.display =
        "block";

    document.getElementById(
        "historyHealthScore"
    ).textContent =
        analytics.healthScore ??
        "—";

    document.getElementById(
        "historyUptime"
    ).textContent =
        analytics.uptimePercentage !==
        undefined
            ? analytics.uptimePercentage +
              "%"
            : "—";

    document.getElementById(
        "historyAverageResponse"
    ).textContent =
        analytics.averageResponseTime !==
        undefined
            ? formatResponseTime(
                analytics.averageResponseTime
            )
            : "—";

    document.getElementById(
        "historyTotalChecks"
    ).textContent =
        analytics.totalChecks ??
        checks.length;

    document.getElementById(
        "historyHealthStatus"
    ).textContent =
        analytics.healthStatus ||
        "—";

    renderResponseHistoryChart(
        checks
    );

    renderHistoryTable(
        checks
    );
}


function clearHistoryPanel() {
    const emptyState =
        document.getElementById(
            "historyEmptyState"
        );

    const panel =
        document.getElementById(
            "historyPanel"
        );

    if (emptyState) {
        emptyState.style.display =
            "block";
    }

    if (panel) {
        panel.style.display =
            "none";
    }
}


function renderResponseHistoryChart(
    checks
) {
    const svg =
        document.getElementById(
            "responseHistoryChart"
        );

    if (!svg) {
        return;
    }

    const width = 900;
    const height = 320;

    const paddingLeft = 60;
    const paddingRight = 30;
    const paddingTop = 30;
    const paddingBottom = 45;

    const chartWidth =
        width -
        paddingLeft -
        paddingRight;

    const chartHeight =
        height -
        paddingTop -
        paddingBottom;

    const orderedChecks =
        [...checks]
            .reverse();

    const values =
        orderedChecks.map(
            function (check) {
                return (
                    Number(
                        check.responseTime
                    ) || 0
                ) * 1000;
            }
        );

    if (values.length === 0) {
        svg.innerHTML = "";
        return;
    }

    const maxValue =
        Math.max(
            ...values,
            1
        );

    const points =
        values.map(
            function (
                value,
                index
            ) {
                const x =
                    values.length === 1
                        ? paddingLeft +
                          chartWidth / 2
                        : paddingLeft +
                          (
                              index /
                              (values.length - 1)
                          ) *
                          chartWidth;

                const y =
                    paddingTop +
                    chartHeight -
                    (
                        value /
                        maxValue
                    ) *
                    chartHeight;

                return {
                    x: x,
                    y: y,
                    value: value
                };
            }
        );

    const linePath =
        points.map(
            function (
                point,
                index
            ) {
                return (
                    index === 0
                        ? "M "
                        : "L "
                ) +
                point.x +
                " " +
                point.y;
            }
        ).join(" ");

    const areaPath =
        linePath +
        " L " +
        points[
            points.length - 1
        ].x +
        " " +
        (
            paddingTop +
            chartHeight
        ) +
        " L " +
        points[0].x +
        " " +
        (
            paddingTop +
            chartHeight
        ) +
        " Z";

    let gridLines = "";

    for (
        let index = 0;
        index <= 4;
        index += 1
    ) {
        const y =
            paddingTop +
            (
                index / 4
            ) *
            chartHeight;

        const label =
            Math.round(
                maxValue *
                (
                    1 -
                    index / 4
                )
            );

        gridLines += `
            <line
                x1="${paddingLeft}"
                y1="${y}"
                x2="${width - paddingRight}"
                y2="${y}"
                class="chart-grid-line"
            ></line>

            <text
                x="10"
                y="${y + 4}"
                class="chart-label"
            >
                ${label} ms
            </text>
        `;
    }

    let pointsMarkup = "";

    points.forEach(
        function (point) {
            pointsMarkup += `
                <circle
                    cx="${point.x}"
                    cy="${point.y}"
                    r="4"
                    class="chart-point"
                ></circle>
            `;
        }
    );

    svg.innerHTML = `
        ${gridLines}

        <path
            d="${areaPath}"
            class="chart-area"
        ></path>

        <path
            d="${linePath}"
            class="chart-line"
        ></path>

        ${pointsMarkup}
    `;
}


function renderHistoryTable(
    checks
) {
    const tbody =
        document.getElementById(
            "historyTableBody"
        );

    if (!tbody) {
        return;
    }

    tbody.innerHTML =
        checks
            .slice(0, 20)
            .map(
                function (check) {
                    const statusClass =
                        check.isUp
                            ? "table-status-up"
                            : "table-status-down";

                    return `
                        <tr>

                            <td>
                                ${formatDate(
                                    check.checkedAt
                                )}
                            </td>

                            <td>
                                <span
                                    class="${statusClass}"
                                >
                                    ${
                                        check.isUp
                                            ? "UP"
                                            : "DOWN"
                                    }
                                </span>
                            </td>

                            <td>
                                ${
                                    check.statusCode ??
                                    "—"
                                }
                            </td>

                            <td>
                                ${
                                    typeof check.responseTime ===
                                    "number"
                                        ? formatResponseTime(
                                            check.responseTime
                                        )
                                        : "—"
                                }
                            </td>

                            <td>
                                ${
                                    check.responseSize !==
                                    null &&
                                    check.responseSize !==
                                    undefined
                                        ? formatResponseSize(
                                            check.responseSize
                                        )
                                        : "—"
                                }
                            </td>

                            <td>
                                ${
                                    check.redirectCount ??
                                    0
                                }
                            </td>

                        </tr>
                    `;
                }
            )
            .join("");
}


async function runCheck(
    websiteId
) {
    try {
        const response =
            await fetch(
                "/api/websites/" +
                websiteId +
                "/check",
                {
                    method: "POST"
                }
            );

        const data =
            await response.json();

        if (!response.ok) {
            throw new Error(
                data.error ||
                "Website check failed."
            );
        }

        await loadDashboard();

    } catch (error) {
        alert(
            error.message
        );
    }
}


function openAddWebsiteModal() {
    editingWebsiteId =
        null;

    document.getElementById(
        "modalEyebrow"
    ).textContent =
        "MONITORING SETUP";

    document.getElementById(
        "modalTitle"
    ).textContent =
        "Add Website";

    document.getElementById(
        "modalButtonIcon"
    ).className =
        "fa-solid fa-plus";

    document.getElementById(
        "modalButtonText"
    ).textContent =
        "Add Website";

    document.getElementById(
        "websiteName"
    ).value = "";

    document.getElementById(
        "websiteUrl"
    ).value = "";

    clearFormMessage();

    document.getElementById(
        "websiteModal"
    ).style.display =
        "flex";
}


function openEditWebsiteModal(
    websiteId
) {
    const website =
        websites.find(
            function (item) {
                return item.id ===
                    websiteId;
            }
        );

    if (!website) {
        return;
    }

    editingWebsiteId =
        websiteId;

    document.getElementById(
        "modalEyebrow"
    ).textContent =
        "WEBSITE SETTINGS";

    document.getElementById(
        "modalTitle"
    ).textContent =
        "Edit Website";

    document.getElementById(
        "modalButtonIcon"
    ).className =
        "fa-solid fa-floppy-disk";

    document.getElementById(
        "modalButtonText"
    ).textContent =
        "Save Changes";

    document.getElementById(
        "websiteName"
    ).value =
        website.name;

    document.getElementById(
        "websiteUrl"
    ).value =
        website.url;

    clearFormMessage();

    document.getElementById(
        "websiteModal"
    ).style.display =
        "flex";
}


function closeWebsiteModal() {
    document.getElementById(
        "websiteModal"
    ).style.display =
        "none";

    editingWebsiteId =
        null;

    clearFormMessage();
}


async function saveWebsite(
    event
) {
    event.preventDefault();

    const name =
        document.getElementById(
            "websiteName"
        ).value.trim();

    const url =
        document.getElementById(
            "websiteUrl"
        ).value.trim();

    if (!name) {
        showFormMessage(
            "Website name is required."
        );

        return;
    }

    if (!url) {
        showFormMessage(
            "Website URL is required."
        );

        return;
    }

    const isEditing =
        Boolean(
            editingWebsiteId
        );

    const endpoint =
        isEditing
            ? "/api/websites/" +
              editingWebsiteId
            : "/api/websites";

    const method =
        isEditing
            ? "PUT"
            : "POST";

    try {
        const response =
            await fetch(
                endpoint,
                {
                    method: method,
                    headers: {
                        "Content-Type":
                            "application/json"
                    },
                    body: JSON.stringify({
                        name: name,
                        url: url
                    })
                }
            );

        const data =
            await response.json();

        if (!response.ok) {
            throw new Error(
                data.error ||
                "Unable to save website."
            );
        }

        closeWebsiteModal();

        await loadDashboard();

    } catch (error) {
        showFormMessage(
            error.message
        );
    }
}


async function deleteWebsite(
    websiteId
) {
    const website =
        websites.find(
            function (item) {
                return item.id ===
                    websiteId;
            }
        );

    if (!website) {
        return;
    }

    const confirmed =
        confirm(
            "Delete " +
            website.name +
            "? This will also remove its monitoring history."
        );

    if (!confirmed) {
        return;
    }

    try {
        const response =
            await fetch(
                "/api/websites/" +
                websiteId,
                {
                    method: "DELETE"
                }
            );

        const data =
            await response.json();

        if (!response.ok) {
            throw new Error(
                data.error ||
                "Unable to delete website."
            );
        }

        await loadDashboard();

    } catch (error) {
        alert(
            error.message
        );
    }
}


function selectAnalysisWebsite(
    websiteId
) {
    const selector =
        document.getElementById(
            "analysisWebsiteSelect"
        );

    if (!selector) {
        return;
    }

    selectedAnalysisWebsiteId =
        websiteId;

    selector.value =
        websiteId;

    const analysisSection =
        document.querySelector(
            ".analysis-section"
        );

    if (analysisSection) {
        analysisSection.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    }
}


function handleAnalysisWebsiteChange(
    event
) {
    selectedAnalysisWebsiteId =
        Number(
            event.target.value
        ) || null;

    clearAnalysisPanel();
}


async function analyzeSelectedWebsite() {
    const selector =
        document.getElementById(
            "analysisWebsiteSelect"
        );

    const button =
        document.getElementById(
            "analyzeWebsiteButton"
        );

    if (!selector || !selector.value) {
        alert(
            "Please select a website first."
        );

        return;
    }

    const websiteId =
        Number(
            selector.value
        );

    selectedAnalysisWebsiteId =
        websiteId;

    if (button) {
        button.disabled =
            true;

        button.innerHTML = `
            <i class="fa-solid fa-spinner fa-spin"></i>
            Analyzing...
        `;
    }

    try {
        const response =
            await fetch(
                "/api/websites/" +
                websiteId +
                "/analyze",
                {
                    method: "POST"
                }
            );

        const data =
            await response.json();

        if (!response.ok) {
            throw new Error(
                data.error ||
                "Website analysis failed."
            );
        }

        currentAnalysis =
            data;

        renderWebsiteAnalysis(
            data
        );

    } catch (error) {
        alert(
            error.message
        );

    } finally {
        if (button) {
            button.disabled =
                false;

            button.innerHTML = `
                <i class="fa-solid fa-magnifying-glass-chart"></i>
                Analyze Website
            `;
        }
    }
}


function renderWebsiteAnalysis(
    data
) {
    const analysis =
        data.analysis || {};

    const emptyState =
        document.getElementById(
            "analysisEmptyState"
        );

    const panel =
        document.getElementById(
            "analysisPanel"
        );

    if (!emptyState || !panel) {
        return;
    }

    emptyState.style.display =
        "none";

    panel.style.display =
        "block";

    const overallScore =
        analysis.overallScore ??
        0;

    const qualityStatus =
        analysis.qualityStatus ||
        "Not Available";

    const seo =
        analysis.seo || {};

    const accessibility =
        analysis.accessibility || {};

    const technical =
        analysis.technical || {};

    const content =
        analysis.content || {};

    document.getElementById(
        "analysisOverallScore"
    ).textContent =
        overallScore;

    document.getElementById(
        "analysisQualityStatus"
    ).textContent =
        qualityStatus;

    document.getElementById(
        "analysisSeoScore"
    ).textContent =
        (seo.score ?? 0) +
        "%";

    document.getElementById(
        "analysisAccessibilityScore"
    ).textContent =
        (accessibility.score ?? 0) +
        "%";

    document.getElementById(
        "analysisTechnicalScore"
    ).textContent =
        (technical.score ?? 0) +
        "%";

    document.getElementById(
        "analysisSeoProgress"
    ).style.width =
        (seo.score ?? 0) +
        "%";

    document.getElementById(
        "analysisAccessibilityProgress"
    ).style.width =
        (accessibility.score ?? 0) +
        "%";

    document.getElementById(
        "analysisTechnicalProgress"
    ).style.width =
        (technical.score ?? 0) +
        "%";

    document.getElementById(
        "analysisWordCount"
    ).textContent =
        content.wordCount ?? 0;

    document.getElementById(
        "analysisH1Count"
    ).textContent =
        content.h1Count ?? 0;

    document.getElementById(
        "analysisH2Count"
    ).textContent =
        content.h2Count ?? 0;

    document.getElementById(
        "analysisImageCount"
    ).textContent =
        content.imageCount ?? 0;

    document.getElementById(
        "analysisImagesWithoutAlt"
    ).textContent =
        content.imagesWithoutAlt ?? 0;

    document.getElementById(
        "analysisLinkCount"
    ).textContent =
        content.linkCount ?? 0;

    document.getElementById(
        "analysisEmptyLinks"
    ).textContent =
        content.emptyLinks ?? 0;

    renderAnalysisChecks(
        "seoChecks",
        seo.checks || {}
    );

    renderAnalysisChecks(
        "accessibilityChecks",
        accessibility.checks || {}
    );

    renderAnalysisChecks(
        "technicalChecks",
        technical.checks || {}
    );

    const analysisSection =
        document.querySelector(
            ".analysis-section"
        );

    if (analysisSection) {
        analysisSection.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    }
}


function renderAnalysisChecks(
    elementId,
    checks
) {
    const container =
        document.getElementById(
            elementId
        );

    if (!container) {
        return;
    }

    const entries =
        Object.entries(
            checks
        );

    if (entries.length === 0) {
        container.innerHTML = `
            <div class="analysis-no-checks">
                No checks available.
            </div>
        `;

        return;
    }

    container.innerHTML =
        entries.map(
            function (
                [key, check]
            ) {
                const passed =
                    Boolean(
                        check.passed
                    );

                const icon =
                    passed
                        ? "fa-check"
                        : "fa-xmark";

                const statusClass =
                    passed
                        ? "analysis-check-pass"
                        : "analysis-check-fail";

                const label =
                    formatAnalysisLabel(
                        key
                    );

                return `
                    <div class="analysis-check-item">

                        <div
                            class="analysis-check-icon ${statusClass}"
                        >
                            <i
                                class="fa-solid ${icon}"
                            ></i>
                        </div>

                        <div class="analysis-check-content">

                            <strong>
                                ${escapeHtml(
                                    label
                                )}
                            </strong>

                            <span>
                                ${formatAnalysisValue(
                                    check.value
                                )}
                            </span>

                        </div>

                        <span
                            class="analysis-check-result ${statusClass}"
                        >
                            ${
                                passed
                                    ? "Passed"
                                    : "Needs Attention"
                            }
                        </span>

                    </div>
                `;
            }
        ).join("");
}


function formatAnalysisLabel(
    value
) {
    return String(value)
        .replace(
            /([A-Z])/g,
            " $1"
        )
        .replace(
            /^./,
            function (
                character
            ) {
                return character.toUpperCase();
            }
        );
}


function formatAnalysisValue(
    value
) {
    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {
        return "Not detected";
    }

    if (
        typeof value ===
        "boolean"
    ) {
        return value
            ? "Enabled"
            : "Not enabled";
    }

    return escapeHtml(
        shortenText(
            String(value),
            80
        )
    );
}


function clearAnalysisPanel() {
    const emptyState =
        document.getElementById(
            "analysisEmptyState"
        );

    const panel =
        document.getElementById(
            "analysisPanel"
        );

    if (emptyState) {
        emptyState.style.display =
            "block";
    }

    if (panel) {
        panel.style.display =
            "none";
    }

    currentAnalysis =
        null;
}


function renderActivity() {
    const container =
        document.getElementById(
            "activityList"
        );

    if (!container) {
        return;
    }

    const activities = [];

    websites.forEach(
        function (website) {
            const checks =
                websiteChecks[
                    website.id
                ] || [];

            checks
                .slice(0, 5)
                .forEach(
                    function (check) {
                        activities.push({
                            website:
                                website.name,
                            check:
                                check
                        });
                    }
                );
        }
    );

    activities.sort(
        function (a, b) {
            return (
                new Date(
                    b.check.checkedAt
                ) -
                new Date(
                    a.check.checkedAt
                )
            );
        }
    );

    if (activities.length === 0) {
        container.innerHTML = `
            <div class="activity-empty">
                <i class="fa-solid fa-clock-rotate-left"></i>
                <span>No monitoring activity yet.</span>
            </div>
        `;

        return;
    }

    container.innerHTML =
        activities
            .slice(0, 10)
            .map(
                function (activity) {
                    const check =
                        activity.check;

                    return `
                        <div class="activity-item">

                            <div class="activity-icon">
                                <i class="fa-solid ${
                                    check.isUp
                                        ? "fa-check"
                                        : "fa-xmark"
                                }"></i>
                            </div>

                            <div class="activity-content">

                                <strong>
                                    ${escapeHtml(
                                        activity.website
                                    )}
                                </strong>

                                <span>
                                    ${
                                        check.isUp
                                            ? "Website responded successfully"
                                            : "Website check failed"
                                    }
                                </span>

                            </div>

                            <time>
                                ${formatDate(
                                    check.checkedAt
                                )}
                            </time>

                        </div>
                    `;
                }
            )
            .join("");
}


function formatResponseTime(
    seconds
) {
    const value =
        Number(seconds);

    if (
        !Number.isFinite(
            value
        )
    ) {
        return "—";
    }

    return (
        Math.round(
            value * 1000
        ) +
        " ms"
    );
}


function formatResponseSize(
    bytes
) {
    const value =
        Number(bytes);

    if (
        !Number.isFinite(
            value
        )
    ) {
        return "—";
    }

    if (value < 1024) {
        return (
            Math.round(value) +
            " B"
        );
    }

    if (value < 1024 * 1024) {
        return (
            (value / 1024).toFixed(1) +
            " KB"
        );
    }

    return (
        (value /
            (1024 * 1024)
        ).toFixed(1) +
        " MB"
    );
}


function shortenText(
    value,
    maxLength
) {
    if (
        value.length <=
        maxLength
    ) {
        return value;
    }

    return (
        value.substring(
            0,
            maxLength - 3
        ) +
        "..."
    );
}


function formatDate(
    value
) {
    if (!value) {
        return "—";
    }

    const date =
        new Date(value);

    if (
        Number.isNaN(
            date.getTime()
        )
    ) {
        return "—";
    }

    return date.toLocaleString(
        [],
        {
            day: "2-digit",
            month: "short",
            hour: "2-digit",
            minute: "2-digit"
        }
    );
}


function escapeHtml(
    value
) {
    return String(value)
        .replace(
            /&/g,
            "&amp;"
        )
        .replace(
            /</g,
            "&lt;"
        )
        .replace(
            />/g,
            "&gt;"
        )
        .replace(
            /"/g,
            "&quot;"
        )
        .replace(
            /'/g,
            "&#039;"
        );
}


function showFormMessage(
    message
) {
    const element =
        document.getElementById(
            "formMessage"
        );

    if (!element) {
        return;
    }

    element.textContent =
        message;

    element.style.display =
        "block";
}


function clearFormMessage() {
    const element =
        document.getElementById(
            "formMessage"
        );

    if (!element) {
        return;
    }

    element.textContent =
        "";

    element.style.display =
        "none";
}


function showDashboardError(
    message
) {
    const grid =
        document.getElementById(
            "websiteGrid"
        );

    if (!grid) {
        return;
    }

    grid.innerHTML = `
        <div class="empty-state error-state">
            <i class="fa-solid fa-triangle-exclamation"></i>
            <h3>Unable to load dashboard</h3>
            <p>
                ${escapeHtml(
                    message
                )}
            </p>
        </div>
    `;
}