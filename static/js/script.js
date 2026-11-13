// Farmer-facing helpers: quantity steppers, form checks, and filter submission.
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".qty-plus, .qty-minus").forEach(function (button) {
    button.addEventListener("click", function () {
      var box = button.closest(".qty-box");
      var input = box.querySelector("input[name='quantity']");
      var current = parseInt(input.value, 10) || 1;
      var min = parseInt(input.min, 10);
      var max = parseInt(input.max, 10);
      if (Number.isNaN(min)) min = 1;
      if (Number.isNaN(max)) max = 500;
      input.value = button.classList.contains("qty-plus")
        ? Math.min(max, current + 1)
        : Math.max(min, current - 1);
    });
  });

  document.querySelectorAll("form.js-validate").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      var existing = form.querySelector(".client-error");
      if (existing) existing.remove();
      var message = "";
      if (form.mobile && !/^\d{10}$/.test(form.mobile.value.trim())) {
        message = "Enter a 10-digit mobile number.";
      } else if (form.password && form.password.value.length < 6) {
        message = "Use at least 6 characters with one letter and one number.";
      } else if (form.confirm_password && form.password.value !== form.confirm_password.value) {
        message = "Passwords do not match.";
      } else if (form.message && form.message.value.trim().length < 10) {
        message = "Please enter a message of at least 10 characters.";
      }
      if (message) {
        event.preventDefault();
        var alertBox = document.createElement("div");
        alertBox.className = "alert alert-danger client-error";
        alertBox.textContent = message;
        form.prepend(alertBox);
        return;
      }
      var button = form.querySelector("[type='submit']");
      if (button) button.disabled = true;
    });
  });

  document.querySelectorAll(".auto-submit").forEach(function (field) {
    field.addEventListener("change", function () {
      field.form.submit();
    });
  });

  document.querySelectorAll("form.js-confirm").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      var text = form.getAttribute("data-confirm") || "Are you sure?";
      if (!window.confirm(text)) event.preventDefault();
    });
  });
});

window.addEventListener("pageshow", function () {
  document.querySelectorAll("form.js-validate [type='submit']").forEach(function (button) {
    button.disabled = false;
  });
});
