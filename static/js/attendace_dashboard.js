document.addEventListener("DOMContentLoaded", () => {
    const table = document.querySelector('.attendance-table');
    const yearFilter = document.getElementById('yearLevelFilter');
    const eventFilter = document.getElementById('eventFilter');
    const nameSearchInput = document.getElementById('nameSearchInput');
    const ayFilter = document.getElementById('academicYearFilter');
    const semFilter = document.getElementById('semesterFilter');
    const exportBtn = document.getElementById('exportBtn');

    // ---------------------- Hours Calculation ----------------------
    function calculateHours(ti, to, required) {
        if (!ti && !to) return required;
        if (ti && to) return 0;
        return required / 2;
    }

    function updateHoursInputStyle(input) {
        const value = parseFloat(input.value) || 0;
        const required = parseFloat(input.dataset.required) || 0;

        input.classList.remove('completed', 'partial');
        if (value >= required) input.classList.add('completed');
        else if (value > 0) input.classList.add('partial');
    }

    function updateTotal(row) {
        let total = 0;
        const inputs = row.querySelectorAll(".hours-input");
        inputs.forEach(input => total += parseFloat(input.value) || 0);
        const totalElement = row.querySelector(".total-hours");
        totalElement.textContent = total.toFixed(2);

        const requiredTotal = Array.from(inputs).reduce((sum, input) => sum + parseFloat(input.dataset.required) || 0, 0);
        if (total >= requiredTotal) {
            totalElement.style.color = '#10b981';
            totalElement.style.background = '#d1fae5';
        } else if (total >= requiredTotal * 0.5) {
            totalElement.style.color = '#f59e0b';
            totalElement.style.background = '#fef3c7';
        } else {
            totalElement.style.color = '#ef4444';
            totalElement.style.background = '#fee2e2';
        }
    }

    function handleCheckboxChange(box) {
        const id = box.dataset.attendanceId;
        const row = box.closest('tr');
        const timeInBox = row.querySelector(`input[name="timein_${id}"]`);
        const timeOutBox = row.querySelector(`input[name="timeout_${id}"]`);
        const hoursInput = row.querySelector(`input[name="hours_${id}"]`);

        if (!hoursInput || !timeInBox || !timeOutBox) return;

        const required = parseFloat(hoursInput.dataset.required) || 0;
        const ti = timeInBox.checked;
        const to = timeOutBox.checked;

        hoursInput.value = calculateHours(ti, to, required);
        updateHoursInputStyle(hoursInput);
        updateTotal(row);
        hoursInput.classList.add('changed');
    }

    function initializeRow(row) {
        const hoursInputs = row.querySelectorAll(".hours-input");
        const checkboxInputs = row.querySelectorAll('input[type="checkbox"]');

        hoursInputs.forEach(input => {
            updateHoursInputStyle(input);

            input.addEventListener("input", () => {
                updateHoursInputStyle(input);
                updateTotal(row);
                input.classList.add('changed');
            });

            input.addEventListener("blur", () => {
                const max = parseFloat(input.dataset.required) || 0;
                const value = parseFloat(input.value) || 0;
                if (value > max) {
                    input.value = max;
                    updateHoursInputStyle(input);
                    updateTotal(row);
                }
            });
        });

        checkboxInputs.forEach(box => {
            box.addEventListener("change", () => handleCheckboxChange(box));
        });

        updateTotal(row);
    }

    document.querySelectorAll("tbody tr").forEach(row => initializeRow(row));

    // ---------------------- Filtering ----------------------
    function applyFilters() {
    const selectedYearLevel = yearFilter.value;
    const selectedEvent = eventFilter.value;
    const nameSearch = nameSearchInput.value.toLowerCase();
    const selectedAY = ayFilter.value;
    const selectedSem = semFilter.value;

    document.querySelectorAll('.student-row').forEach(row => {
        const nameCell = row.querySelector('.name-col');
        if (!nameCell) return;  // safety check

        const rowName = nameCell.textContent.toLowerCase();
        const rowYearLevel = row.dataset.yearLevel;
        const rowAY = row.dataset.academicYear;
        const rowSem = row.dataset.semesterId;

        let matchesName = !nameSearch || rowName.includes(nameSearch);
        let matchesYearLevel = !selectedYearLevel || rowYearLevel === selectedYearLevel;
        let matchesAY = !selectedAY || rowAY === selectedAY;
        let matchesSem = !selectedSem || rowSem === selectedSem;
        let matchesEvent = true;

        if (selectedEvent) {
            matchesEvent = row.querySelector(`[data-event-id="${selectedEvent}"]`) !== null;
        }

        // Hide row if any filter fails
        row.style.display = (matchesName && matchesYearLevel && matchesEvent && matchesAY && matchesSem) ? "" : "none";
    });
}

// Attach listeners correctly
[nameSearchInput, yearFilter, eventFilter, ayFilter, semFilter].forEach(el => {
    if (!el) return;
    if (el.tagName === 'INPUT') {
        el.addEventListener('input', applyFilters);
    } else {
        el.addEventListener('change', applyFilters);
    }
});


    // ---------------------- Export CSV ----------------------
    if (exportBtn) {
        exportBtn.addEventListener('click', () => {
            const rows = [];
            const headers = ['Student ID', 'Name', 'Year Level', 'Total Hours'];
            document.querySelectorAll('th.event-header').forEach(header => {
                const eventName = header.querySelector('strong').textContent;
                headers.push(`${eventName} - Time In`);
                headers.push(`${eventName} - Time Out`);
                headers.push(`${eventName} - Hours`);
            });
            rows.push(headers.join(','));

            document.querySelectorAll('.student-row').forEach(row => {
                if (row.style.display !== 'none') {
                    const cells = [
                        row.cells[0].textContent,
                        row.cells[1].textContent,
                        row.cells[2].textContent,
                        row.cells[3].textContent
                    ];

                    for (let i = 4; i < row.cells.length; i += 3) {
                        const timeIn = row.cells[i].querySelector('input[type="checkbox"]').checked;
                        const timeOut = row.cells[i + 1].querySelector('input[type="checkbox"]').checked;
                        const hours = row.cells[i + 2].querySelector('input[type="number"]').value;

                        cells.push(timeIn ? 'Yes' : 'No');
                        cells.push(timeOut ? 'Yes' : 'No');
                        cells.push(hours);
                    }

                    rows.push(cells.join(','));
                }
            });

            const csvContent = rows.join('\n');
            const blob = new Blob([csvContent], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `attendance_data_${new Date().toISOString().split('T')[0]}.csv`;
            a.click();
            window.URL.revokeObjectURL(url);
        });
    }

    // ---------------------- Form Submission ----------------------
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', () => {
            const submitBtn = form.querySelector('.btn-primary');
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="btn-icon">⏳</span>Saving...';

            setTimeout(() => {
                document.querySelectorAll('.changed').forEach(el => el.classList.remove('changed'));
            }, 1000);
        });
    }

    // ---------------------- Keyboard Shortcut ----------------------
    document.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 's') {
            e.preventDefault();
            form.dispatchEvent(new Event('submit'));
        }
    });

    console.log('Attendance Dashboard initialized successfully!');
});
