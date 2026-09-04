// =========================================================
// EVENTHUB FINAL JAVASCRIPT
// =========================================================

// Confirm event deletion
function confirmDelete() {
    return confirm(
        "Are you sure you want to delete this event?\n\n" +
        "All related bookings, attendance records and feedback " +
        "will also be removed."
    );
}


// Simple form protection against accidental double submission
document.addEventListener("DOMContentLoaded", function () {

    const forms = document.querySelectorAll(
        "form[data-disable-submit]"
    );

    forms.forEach(function (form) {

        form.addEventListener("submit", function () {

            const button = form.querySelector(
                "button[type='submit']"
            );

            if (button) {

                button.disabled = true;

                button.style.opacity = "0.7";

                button.textContent = "Processing...";

            }

        });

    });

});