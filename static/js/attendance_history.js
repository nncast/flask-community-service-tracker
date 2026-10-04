document.addEventListener("DOMContentLoaded", () => {
    const timeFilter = document.getElementById('timeFilter');
    const searchInput = document.getElementById('searchInput');
    const historyRows = document.querySelectorAll('.history-row');
    const noMatch = document.getElementById('noHistoryMatch');

    // YYYY-MM-DD in local time (toISOString() would give the UTC date, which is
    // a day off for part of the day in UTC+8)
    function localDate(daysAgo) {
        const d = new Date();
        d.setDate(d.getDate() - daysAgo);
        const pad = n => String(n).padStart(2, '0');
        return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
    }

    // Filter functionality
    function filterTable() {
        const timeValue = timeFilter.value;
        const searchValue = searchInput.value.trim().toLowerCase();

        const today = localDate(0);
        const weekAgo = localDate(7);
        const monthAgo = localDate(30);
        let visible = 0;

        historyRows.forEach(row => {
            const rowDate = row.dataset.date;
            const rowStudent = row.dataset.student.toLowerCase();
            const rowEvent = row.dataset.event.toLowerCase();

            // Time filter
            let showTime = true;
            if (timeValue === 'today' && rowDate !== today) showTime = false;
            if (timeValue === 'week' && rowDate < weekAgo) showTime = false;
            if (timeValue === 'month' && rowDate < monthAgo) showTime = false;

            // Search filter
            const showSearch = !searchValue ||
                rowStudent.includes(searchValue) ||
                rowEvent.includes(searchValue);

            const show = showTime && showSearch;
            row.style.display = show ? '' : 'none';
            if (show) visible++;
        });

        if (noMatch) noMatch.style.display = (historyRows.length && !visible) ? '' : 'none';
    }

    // Initialize event listeners
    timeFilter.addEventListener('change', filterTable);
    searchInput.addEventListener('input', filterTable);
    filterTable();
});
