document.addEventListener("DOMContentLoaded", () => {
    const timeFilter = document.getElementById('timeFilter');
    const searchInput = document.getElementById('searchInput');
    const historyRows = document.querySelectorAll('.history-row');

    // Filter functionality
    function filterTable() {
        const timeValue = timeFilter.value;
        const searchValue = searchInput.value.toLowerCase();
        
        const today = new Date().toISOString().split('T')[0];
        const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
        const monthAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
        
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
            
            row.style.display = showTime && showSearch ? '' : 'none';
        });
    }

    // Initialize event listeners
    timeFilter.addEventListener('change', filterTable);
    searchInput.addEventListener('input', filterTable);
    
    console.log('Attendance History initialized successfully!');
});