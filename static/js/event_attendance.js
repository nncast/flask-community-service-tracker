document.addEventListener("DOMContentLoaded", () => {
    const table = document.querySelector(".event-attendance-table");
    if (!table) return;
    const requiredHours = parseFloat(table.dataset.requiredHours) || 0;

    // Same rule as the server: signed in and out = 0 owed, one of them = half, neither = full
    function updateRow(row) {
        const [timedIn, timedOut] = Array.from(row.querySelectorAll('input[type="checkbox"]')).map(cb => cb.checked);
        const badge = row.querySelector(".hours-badge");
        let hours = requiredHours;
        let state = "pending";
        if (timedIn && timedOut) {
            hours = 0;
            state = "completed";
        } else if (timedIn || timedOut) {
            hours = requiredHours / 2;
            state = "partial";
        }
        badge.textContent = Number(hours.toFixed(2)).toString();
        badge.className = `hours-badge ${state}`;
    }

    table.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
        checkbox.addEventListener("change", function () {
            const row = this.closest("tr");
            updateRow(row);

            // Visual feedback
            row.style.background = "#f0f9ff";
            setTimeout(() => {
                row.style.background = "";
            }, 1000);
        });
    });

    // Form submission feedback
    const form = table.closest("form");
    form.addEventListener("submit", function () {
        const submitBtn = this.querySelector(".btn-primary");
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="btn-icon"><svg class="icon icon-spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg></span>Saving...';
        }
    });
});
