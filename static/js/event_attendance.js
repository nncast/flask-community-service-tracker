document.addEventListener("DOMContentLoaded", () => {
    const table = document.querySelector(".event-attendance-table");
    if (!table) return;
    const requiredHours = parseFloat(table.dataset.requiredHours) || 0;
    const saveUrl = table.dataset.saveUrl;
    const rows = Array.from(table.querySelectorAll("tbody tr"));
    const entry = document.getElementById("quickEntry");
    const status = document.getElementById("sheetStatus");
    const noMatch = document.getElementById("noRowsMatch");
    const chips = Array.from(document.querySelectorAll(".status-chips .chip"));
    let chipFilter = "";

    const boxes = row => [row.querySelector(".att-in"), row.querySelector(".att-out")];
    const nameOf = row => row.querySelector(".student-name").textContent;

    // Same rule as the server: signed in and out = 0 owed, one of them = half, neither = full
    function stateOf(row) {
        const [timedIn, timedOut] = boxes(row).map(cb => cb.checked);
        return timedIn && timedOut ? "completed" : (timedIn || timedOut ? "partial" : "pending");
    }

    function paint(row) {
        const state = stateOf(row);
        const hours = { completed: 0, partial: requiredHours / 2, pending: requiredHours }[state];
        const badge = row.querySelector(".hours-badge");
        badge.textContent = Number(hours.toFixed(2)).toString();
        badge.className = `hours-badge ${state}`;
        row.dataset.state = state;
    }

    function refresh() {
        const term = entry.value.trim().toLowerCase();
        const counts = { all: rows.length, pending: 0, partial: 0, completed: 0 };
        let shown = 0;
        rows.forEach(row => {
            counts[row.dataset.state]++;
            const visible = (!term || row.dataset.search.includes(term)) && (!chipFilter || row.dataset.state === chipFilter);
            row.hidden = !visible;
            if (visible) shown++;
        });
        document.querySelectorAll("[data-count]").forEach(el => (el.textContent = counts[el.dataset.count]));
        noMatch.hidden = shown > 0;
    }

    function say(message, isError) {
        status.textContent = message;
        status.classList.toggle("error", Boolean(isError));
    }

    function flashRow(row, className) {
        row.classList.remove("just-saved", "save-failed");
        void row.offsetWidth;   // restart the animation
        row.classList.add(className);
    }

    async function save(row, message) {
        const [inBox, outBox] = boxes(row);
        paint(row);
        refresh();
        try {
            await saveAttendance(saveUrl, row.dataset.attId, inBox.checked, outBox.checked, "sheet");
            inBox.dataset.saved = inBox.checked;
            outBox.dataset.saved = outBox.checked;
            flashRow(row, "just-saved");
            if (message) say(message);
        } catch (error) {
            // Put the boxes back to what the database has
            inBox.checked = inBox.dataset.saved === "true";
            outBox.checked = outBox.dataset.saved === "true";
            paint(row);
            refresh();
            flashRow(row, "save-failed");
            say(error.message, true);
        }
    }

    rows.forEach(row => {
        boxes(row).forEach(cb => {
            cb.dataset.saved = cb.checked;
            cb.addEventListener("change", () => save(row));
        });
        paint(row);
    });

    // Enter: the exact student ID, or the only student left in the list, takes their next step
    entry.addEventListener("input", refresh);
    entry.addEventListener("keydown", event => {
        if (event.key !== "Enter") return;
        event.preventDefault();
        const term = entry.value.trim().toLowerCase();
        if (!term) return;
        const visible = rows.filter(row => !row.hidden);
        const row = rows.find(r => r.dataset.sid === term) || (visible.length === 1 ? visible[0] : null);
        if (!row) {
            say(visible.length ? `${visible.length} students match. Keep typing or scan the ID.` : `No student matches "${entry.value.trim()}".`, true);
            return;
        }
        const [inBox, outBox] = boxes(row);
        entry.value = "";
        if (!inBox.checked) {
            inBox.checked = true;
            save(row, `Signed in: ${nameOf(row)}`);
        } else if (!outBox.checked) {
            outBox.checked = true;
            save(row, `Signed out: ${nameOf(row)}`);
        } else {
            refresh();
            say(`${nameOf(row)} has already signed in and out.`);
        }
        row.scrollIntoView({ block: "nearest" });
    });

    chips.forEach(chip => chip.addEventListener("click", () => {
        chipFilter = chip.dataset.filter;
        chips.forEach(c => {
            c.classList.toggle("active", c === chip);
            c.setAttribute("aria-pressed", String(c === chip));
        });
        refresh();
    }));

    refresh();
});
