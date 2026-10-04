// Shared logic for the Create Event and Edit Event forms.
// Shows only the year levels of the academic year that the chosen date falls in.
document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector(".event-form");
    const dataEl = document.getElementById("academicYearsData");
    if (!form || !dataEl) return;

    const academicYears = JSON.parse(dataEl.textContent);
    const dateInput = form.querySelector('input[name="date"]');
    const container = document.getElementById("yearLevelContainer");
    const hint = document.getElementById("yearLevelHint");
    const allCheckbox = container.querySelector(".all-checkbox input");
    const labels = Array.from(container.querySelectorAll("#yearLevelGrid .checkbox-label"));
    // Edit page: "all" or a comma separated list of year level IDs
    const initialTargets = form.dataset.targets || "";
    const noYearMessage = hint.textContent.trim();
    const pickDateMessage = "Pick a date first. The year levels of that academic year will appear here.";
    let currentAyId = null;

    // An academic year covers the span from its earliest semester start to its latest semester end
    function academicYearFor(dateStr) {
        return academicYears.find(ay => {
            const starts = ay.semesters.map(s => s.start).filter(Boolean).sort();
            const ends = ay.semesters.map(s => s.end).filter(Boolean).sort();
            if (!starts.length || !ends.length) return false;
            return dateStr >= starts[0] && dateStr <= ends[ends.length - 1];
        });
    }

    function enabledBoxes() {
        return labels.map(l => l.querySelector("input")).filter(cb => !cb.disabled);
    }

    function syncAllCheckbox() {
        const boxes = enabledBoxes();
        allCheckbox.disabled = boxes.length === 0;
        allCheckbox.checked = boxes.length > 0 && boxes.every(cb => cb.checked);
    }

    function update(isInitial) {
        if (!dateInput.value) {
            container.style.display = "none";
            hint.textContent = pickDateMessage;
            hint.style.display = "block";
            return;
        }
        hint.textContent = noYearMessage;
        const ay = academicYearFor(dateInput.value);
        const ayChanged = (ay ? ay.id : null) !== currentAyId;
        currentAyId = ay ? ay.id : null;

        container.style.display = ay ? "block" : "none";
        hint.style.display = ay ? "none" : "block";

        labels.forEach(label => {
            const cb = label.querySelector("input");
            const visible = ay && Number(label.dataset.academicYear) === ay.id;
            label.style.display = visible ? "" : "none";
            cb.disabled = !visible;
            if (!visible) {
                cb.checked = false;
            } else if (isInitial && initialTargets) {
                cb.checked = initialTargets === "all" || initialTargets.split(",").includes(cb.value);
            } else if (ayChanged) {
                cb.checked = true;   // new academic year: target all of its year levels by default
            }
        });
        syncAllCheckbox();
    }

    allCheckbox.addEventListener("change", () => {
        enabledBoxes().forEach(cb => (cb.checked = allCheckbox.checked));
    });
    labels.forEach(label => label.querySelector("input").addEventListener("change", syncAllCheckbox));
    dateInput.addEventListener("change", () => update(false));

    form.addEventListener("submit", event => {
        if (dateInput.value && !enabledBoxes().some(cb => cb.checked)) {
            event.preventDefault();
            alert("Select at least one target year level.");
        }
    });

    update(true);
});
