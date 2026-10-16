/* =============================================================
   theme.js — /admin/home 라이트/다크 테마 전환
   · 초기 테마는 base.html <head> 인라인 스크립트가 <html data-theme> 로 먼저 설정한다
     (첫 화면 깜빡임 방지). 이 파일은 토프바 토글 버튼만 담당한다.
   · 사용자가 고른 값은 localStorage("ah-theme") 에 저장된다. 저장값이 없으면
     OS 설정(prefers-color-scheme)을 따르고, OS 설정이 바뀌면 즉시 반영한다.
   · <html> 은 부분 로딩(partial-nav.js)으로 교체되지 않으므로 페이지 이동 후에도 유지된다.
   ============================================================= */
(function () {
  "use strict";

  var KEY = "ah-theme";
  var root = document.documentElement;
  var mql = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;

  function stored() {
    try {
      var v = localStorage.getItem(KEY);
      return v === "light" || v === "dark" ? v : null;
    } catch (e) {
      return null;
    }
  }

  function current() {
    return root.getAttribute("data-theme") === "dark" ? "dark" : "light";
  }

  function syncButton() {
    var btn = document.getElementById("ah-theme-toggle");
    if (!btn) return;
    var label = current() === "dark" ? "라이트 모드로 전환" : "다크 모드로 전환";
    btn.setAttribute("aria-label", label);
    btn.setAttribute("title", label);
  }

  function apply(theme) {
    root.setAttribute("data-theme", theme);
    syncButton();
  }

  document.addEventListener("click", function (e) {
    var btn = e.target.closest ? e.target.closest("#ah-theme-toggle") : null;
    if (!btn) return;
    var next = current() === "dark" ? "light" : "dark";
    try {
      localStorage.setItem(KEY, next);
    } catch (err) {
      /* 저장 불가(사생활 보호 모드 등) — 이번 페이지에만 적용 */
    }
    apply(next);
  });

  // 직접 고른 적이 없으면 OS 설정 변경을 따라간다.
  if (mql) {
    var onChange = function (ev) {
      if (stored()) return;
      apply(ev.matches ? "dark" : "light");
    };
    if (mql.addEventListener) mql.addEventListener("change", onChange);
    else if (mql.addListener) mql.addListener(onChange);
  }

  syncButton();
})();
