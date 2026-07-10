/* =============================================================
   interactions.js — hover/active 등 인터랙션 + Nav pill 이동
   유리 컴포넌트의 미세 상호작용을 담당. vanilla JS.

   부분 로딩(partial-nav.js) 대응: init() 은 멱등이며 "ah:content-loaded"
   이벤트로 다시 호출된다. 이미 리스너를 붙인 nav 는 data-ah-nav-wired 로
   표시해 중복 바인딩을 막고, 위치(인디케이터)만 다시 계산한다.
   서브내비처럼 새로 삽입된 nav 는 이때 처음 배선된다.
   ============================================================= */
(function () {
  "use strict";

  var reduceMotion =
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* -----------------------------------------------------------
     Nav 배선 — 활성 하이라이트(원형 pill)의 위치 관리 + 클릭 이동.
     · 원(인디케이터)은 "선택(활성)된 탭"에만 머문다.
     · 호버로는 이동하지 않는다(탭 자체 그림자만; components.css :hover).
     · 클릭(선택) 시에만 클릭한 탭으로 슬라이드 이동한다.
     ----------------------------------------------------------- */
  function wireNav(nav) {
    var items = nav.querySelectorAll(".glass-nav__item");
    if (!items.length) return;
    var indicator = nav.querySelector(".glass-nav__indicator");

    function moveTo(item, withTransition) {
      if (!indicator) return;
      if (!withTransition) indicator.style.transition = "none";
      nav.style.setProperty("--nav-ind-x", item.offsetLeft + "px");
      nav.style.setProperty("--nav-ind-w", item.offsetWidth + "px");
      nav.style.setProperty("--nav-ind-y", item.offsetTop + "px");
      nav.style.setProperty("--nav-ind-h", item.offsetHeight + "px");
      indicator.classList.add("is-visible");
      if (!withTransition) {
        // 강제 리플로우 후 transition 복원 — 초기 배치가 슬라이드로 보이지 않도록 함
        // eslint-disable-next-line no-unused-expressions
        indicator.offsetHeight;
        indicator.style.transition = "";
      }
    }

    function getActiveItem() {
      var active = null;
      items.forEach(function (i) {
        if (i.classList.contains("is-active")) active = i;
      });
      return active;
    }

    function settle() {
      if (!indicator) return;
      var active = getActiveItem();
      if (active) moveTo(active, false);
      else indicator.classList.remove("is-visible");
    }

    // 재초기화 시에는 위치만 다시 잡고 리스너는 다시 붙이지 않는다.
    if (nav.dataset.ahNavWired) {
      settle();
      return;
    }
    nav.dataset.ahNavWired = "1";
    nav._ahSettle = settle;

    items.forEach(function (item) {
      item.addEventListener("click", function () {
        items.forEach(function (i) {
          i.classList.remove("is-active");
        });
        item.classList.add("is-active");
        // 클릭(선택) 시에만 원이 슬라이드 이동. preventDefault 하지 않는다.
        if (!reduceMotion) moveTo(item, true);
      });
    });

    settle();
  }

  /* -----------------------------------------------------------
     포인터 위치에 따른 유리 하이라이트 (선택적, 미세 효과)
     reduced-motion 이면 비활성.
     ----------------------------------------------------------- */
  function initGlassSheen() {
    if (reduceMotion) return;
    document
      .querySelectorAll("[data-glass-sheen]:not([data-sheen-wired])")
      .forEach(function (el) {
        el.dataset.sheenWired = "1";
        el.addEventListener("pointermove", function (e) {
          var rect = el.getBoundingClientRect();
          var x = ((e.clientX - rect.left) / rect.width) * 100;
          var y = ((e.clientY - rect.top) / rect.height) * 100;
          el.style.setProperty("--sheen-x", x + "%");
          el.style.setProperty("--sheen-y", y + "%");
        });
      });
  }

  /* -----------------------------------------------------------
     Modal 배선 — data-modal-open="ID" 로 열고, [data-modal-close]
     (닫기 버튼/오버레이) 클릭이나 Esc 로 닫는다.
     이벤트 위임을 document 에 한 번만 걸어 부분 로딩으로 콘텐츠가
     교체돼도 재배선이 필요 없다.
     ----------------------------------------------------------- */
  function openModal(modal) {
    if (!modal) return;
    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("ah-modal-open");
  }

  function closeModal(modal) {
    if (!modal) return;
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
    if (!document.querySelector(".ah-modal.is-open")) {
      document.body.classList.remove("ah-modal-open");
    }
  }

  function initModals() {
    if (document._ahModalWired) return;
    document._ahModalWired = "1";

    document.addEventListener("click", function (e) {
      if (!e.target.closest) return;
      var opener = e.target.closest("[data-modal-open]");
      if (opener) {
        openModal(document.getElementById(opener.getAttribute("data-modal-open")));
        return;
      }
      var closer = e.target.closest("[data-modal-close]");
      if (closer) closeModal(closer.closest(".ah-modal"));
    });

    document.addEventListener("keydown", function (e) {
      if (e.key !== "Escape" && e.keyCode !== 27) return;
      document.querySelectorAll(".ah-modal.is-open").forEach(closeModal);
    });
  }

  function init() {
    document.querySelectorAll(".glass-nav").forEach(wireNav);
    initGlassSheen();
    initModals();
  }

  // 창 크기 변경 시 모든 nav 인디케이터 위치 재계산 (전역에 한 번만 바인딩)
  window.addEventListener("resize", function () {
    document.querySelectorAll(".glass-nav").forEach(function (nav) {
      if (nav._ahSettle) nav._ahSettle();
    });
  });

  // 부분 로딩으로 콘텐츠가 교체되면 새 nav 배선 + 활성 위치 재계산
  document.addEventListener("ah:content-loaded", init);

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
