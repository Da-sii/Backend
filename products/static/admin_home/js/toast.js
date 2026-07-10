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

  function init() {
    var container = document.querySelector(".ah-toast-container");
    if (!container) return;

    container.querySelectorAll(".ah-toast").forEach(initToast);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
