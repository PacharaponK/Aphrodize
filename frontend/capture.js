const openCamera = document.querySelector("#open-camera");
const takePhoto = document.querySelector("#take-photo");
const usePhoto = document.querySelector("#use-photo");
const chooseImage = document.querySelector("#choose-image");
const imageInput = document.querySelector("#image-input");
const video = document.querySelector("#camera-preview");
const preview = document.querySelector("#photo-preview");
const guide = document.querySelector("#capture-guide");
const message = document.querySelector("#camera-message");
let stream;

function setPhoto(source) {
  preview.src = source;
  preview.hidden = false;
  video.hidden = true;
  guide.hidden = true;
  takePhoto.hidden = true;
  usePhoto.hidden = false;
  openCamera.hidden = true;
  chooseImage.hidden = true;
  message.textContent = "ตรวจสอบภาพแล้วกด “ใช้ภาพนี้” เพื่อไปขั้นวิเคราะห์";
  stream?.getTracks().forEach((track) => track.stop());
  stream = undefined;
}

openCamera.addEventListener("click", async () => {
  if (!navigator.mediaDevices?.getUserMedia) {
    message.textContent = "อุปกรณ์หรือ browser นี้ไม่รองรับกล้อง กรุณาเลือกภาพแทน";
    return;
  }
  try {
    stream?.getTracks().forEach((track) => track.stop());
    stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false });
    video.srcObject = stream;
    video.hidden = false;
    guide.hidden = true;
    takePhoto.hidden = false;
    openCamera.hidden = true;
    message.textContent = "จัดใบหน้าให้อยู่กึ่งกลางกรอบ แล้วกดถ่ายภาพ";
  } catch (error) {
    message.textContent = error.name === "NotAllowedError" ? "ยังไม่ได้อนุญาตให้ใช้กล้อง กรุณาอนุญาตกล้องจาก browser หรือเลือกภาพแทน" : "เปิดกล้องไม่ได้ โปรดลองเปิดผ่าน https หรือ http://localhost แล้วลองใหม่ หรือเลือกภาพแทน";
  }
});

takePhoto.addEventListener("click", () => {
  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext("2d").drawImage(video, 0, 0);
  setPhoto(canvas.toDataURL("image/jpeg", 0.92));
});

imageInput.addEventListener("change", () => {
  const file = imageInput.files?.[0];
  if (!file) return;
  if (file.size > 10 * 1024 * 1024) {
    message.textContent = "ไฟล์มีขนาดเกิน 10 MiB กรุณาเลือกภาพที่เล็กกว่า";
    return;
  }
  setPhoto(URL.createObjectURL(file));
});

usePhoto.addEventListener("click", () => window.location.assign("result-detail.html"));
window.addEventListener("pagehide", () => stream?.getTracks().forEach((track) => track.stop()));
