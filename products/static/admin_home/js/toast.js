/* =============================================================
   toast.js — 우측 상단 토스트 알림 (Django messages)
   base.html 이 렌더링한 .ah-toast-container 안의 .ah-toast 를
   일정 시간 후 자동으로 닫는다.
   prefers-reduced-motion 이면 애니메이션 없이 즉시 제거한다.
   ============================================================= */
(function () {
  "use strict";

  var AUTO_DISMISS_MS = 3000;
  var LEAVE_MS = 240;

  function prefersReducedMotion() {
    return (
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    );
  }

  function dismiss(toast) {
    if (!toast || toast.dataset.dismissing === "true") return;
    toast.dataset.dismissing = "true";

    if (prefersReducedMotion()) {
      toast.remove();
      return;
    }

    toast.classList.add("is-leaving");
    setTimeout(function () {
      toast.remove();
    }, LEAVE_MS);
  }

  function initToast(toast) {
    setTimeout(function () {
      dismiss(toast);
    }, AUTO_DISMISS_MS);
  }

  function getContainer() {
    var container = document.querySelector(".ah-toast-container");
    if (!container) {
      container = document.createElement("div");
      container.className = "ah-toast-container";
      container.setAttribute("aria-live", "polite");
      container.setAttribute("aria-atomic", "true");
      document.body.appendChild(container);
    }
    return container;
  }

  // 프로그램적으로 토스트를 띄운다(AJAX 후 등). tag: success/error/warning/info.
  // base.html 이 렌더한 Django messages 토스트와 동일한 마크업/동작을 재사용한다.
  function showToast(message, tag) {
    var container = getContainer();
    var toast = document.createElement("div");
    toast.className = "ah-toast";
    toast.setAttribute("data-toast-tag", tag || "info");
    toast.setAttribute("role", "status");
    var span = document.createElement("span");
    span.className = "ah-toast__msg";
    span.textContent = message == null ? "" : String(message);
    toast.appendChild(span);
    container.appendChild(toast);
    initToast(toast);
    return toast;
  }

  function init() {
    var container = document.querySelector(".ah-toast-container");
    if (!container) return;

    container.querySelectorAll(".ah-toast").forEach(initToast);
  }

  // 다른 스크립트(페이지 extra_js)에서 호출할 수 있도록 전역으로 노출한다.
  window.ahToast = showToast;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
