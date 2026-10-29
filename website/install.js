"use strict";
document.querySelectorAll("[data-copy]").forEach((button) => {
  button.addEventListener("click", async () => {
    const target = document.getElementById(button.dataset.copy);
    const status = document.getElementById("copy-status");
    try {
      await navigator.clipboard.writeText(target.textContent.trim());
      button.textContent = "Copied";
      status.textContent =
        "Command copied. Review the instructions before running it.";
      setTimeout(() => {
        button.textContent = "Copy";
      }, 2000);
    } catch {
      status.textContent =
        "Could not copy automatically. Select the command and copy it manually.";
    }
  });
});
