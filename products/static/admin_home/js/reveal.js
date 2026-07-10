/* =============================================================
   reveal.js — IntersectionObserver 스크롤 등장
   .reveal 요소가 뷰포트에 들어오면 .is-visible 부여.
   data-reveal-stagger 컨테이너의 자식은 순서대로 지연(stagger).
   prefers-reduced-motion 시 즉시 표시.

   부분 로딩(partial-nav.js) 대응: init() 은 멱등(idempotent)이며,
   "ah:content-loaded" 이벤트로 다시 호출되면 새로 삽입된 .reveal 만 처리한다.
   (이미 처리한 요소는 data-reveal-wired 로 표시해 중복 관찰을 막는다.)
   ============================================================= */
(function () {
  "use strict";

  var observer = null;

  function getObserver() {
    if (observer) return observer;
    observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -8% 0px" }
    );
    return observer;
  }

  function init() {
    var reduceMotion =
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // stagger index 부여 (아직 처리 안 한 그룹만)
    document
      .querySelectorAll("[data-reveal-stagger]:not([data-stagger-wired])")
      .forEach(function (group) {
        group.dataset.staggerWired = "1";
        var items = group.querySelectorAll(".reveal");
        items.forEach(function (item, i) {
          item.style.setProperty("--reveal-index", i);
        });
      });

    // 아직 처리 안 한 .reveal 만 대상으로 한다.
    var targets = document.querySelectorAll(".reveal:not([data-reveal-wired])");
    if (!targets.length) return;

    targets.forEach(function (el) {
      el.dataset.revealWired = "1";
    });

    if (reduceMotion || !("IntersectionObserver" in window)) {
      targets.forEach(function (el) {
        el.classList.add("is-visible");
      });
      return;
    }

    var io = getObserver();
    targets.forEach(function (el) {
      io.observe(el);
    });
  }

  // 부분 로딩으로 콘텐츠가 교체되면 새 .reveal 을 다시 관찰한다.
  document.addEventListener("ah:content-loaded", init);

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
