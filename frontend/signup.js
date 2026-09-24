const form = document.querySelector("#signup-form");
const steps = [...document.querySelectorAll(".signup-step")];
const progress = [...document.querySelectorAll(".signup-progress li")];
const message = document.querySelector("#form-message");
const password = document.querySelector("#password");
const togglePassword = document.querySelector("#toggle-password");
let currentStep = 0;

function showStep(index) {
  currentStep = index;
  steps.forEach((step, stepIndex) => {
    const active = stepIndex === index;
    step.hidden = !active;
    step.classList.toggle("active", active);
  });
  progress.forEach((item, itemIndex) => {
    const active = itemIndex === index;
    item.classList.toggle("active", active);
    item.toggleAttribute("aria-current", active);
  });
  message.textContent = "";
}

togglePassword.addEventListener("click", () => {
  const hidden = password.type === "password";
  password.type = hidden ? "text" : "password";
  togglePassword.textContent = hidden ? "ซ่อน" : "แสดง";
});

document.querySelectorAll(".next-step").forEach((button) => button.addEventListener("click", () => {
  const fields = [...steps[currentStep].querySelectorAll("input[required]")];
  if (!fields.every((field) => field.checkValidity())) {
    fields.find((field) => !field.checkValidity())?.reportValidity();
    return;
  }
  showStep(currentStep + 1);
}));
document.querySelectorAll(".previous-step").forEach((button) => button.addEventListener("click", () => showStep(currentStep - 1)));

form.addEventListener("submit", (event) => {
  event.preventDefault();
  if (!form.checkValidity()) {
    message.textContent = "กรุณายืนยันความยินยอมก่อนสร้างบัญชี";
    form.reportValidity();
    return;
  }
  window.location.assign("index.html");
});
