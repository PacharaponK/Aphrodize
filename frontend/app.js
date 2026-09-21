const dialogs = document.querySelectorAll("dialog");

function openDialog(id) {
  const target = document.getElementById(id);
  if (target) target.showModal();
}

document.querySelectorAll("[data-open]").forEach((button) => {
  button.addEventListener("click", () => {
    const current = button.closest("dialog");
    if (current) current.close();
    openDialog(button.dataset.open);
  });
});

document.querySelectorAll("[data-close]").forEach((button) => {
  button.addEventListener("click", () => button.closest("dialog").close());
});

dialogs.forEach((dialog) => dialog.addEventListener("click", (event) => {
  if (event.target === dialog) dialog.close();
}));
