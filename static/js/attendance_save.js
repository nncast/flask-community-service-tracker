// Saves one attendance record the moment a box is ticked (event sheet and attendance dashboard).
// Saves of the same record run one after another, so the last tick always wins.
const attendanceQueues = new Map();

function saveAttendance(saveUrl, id, timedIn, timedOut, via) {
    const previous = attendanceQueues.get(id) || Promise.resolve();
    const next = previous.catch(() => {}).then(async () => {
        const response = await fetch(saveUrl + id, {
            method: "POST",
            headers: { "Accept": "application/json" },
            body: new URLSearchParams({ timed_in: timedIn ? "1" : "0", timed_out: timedOut ? "1" : "0", via })
        });
        // A finished session redirects to the sign-in page instead of answering
        if (response.redirected) throw new Error("Your session ended. Sign in again, then redo this change.");
        if (!response.ok) throw new Error("Not saved. Check the connection and tick the box again.");
        return (await response.json()).hours;
    });
    attendanceQueues.set(id, next);
    return next;
}
