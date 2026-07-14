/* =============================================================
   partial-nav.js — /admin/home 탭 부분 로딩(SPA식 전환)
   상단 탭 바(#ah-topnav)와 로그아웃 바는 그대로 두고, #ah-content 안의
   내용만 교체한다. 전체 페이지 리로드가 사라져 탭 전환이 부드럽다.

   동작:
   · 내부 링크(href 가 /admin/home/ 로 시작) 클릭을 가로채 fetch 로 부분 렌더를
     받아온다(X-Partial-Nav 헤더). 서버는 셸 없이 콘텐츠만 반환한다.
   · #ah-content 를 교체하고, innerHTML 로는 실행되지 않는 <script> 를 재실행한 뒤
     "ah:content-loaded" 이벤트를 발생시켜 reveal/interactions 를 재초기화한다.
   · document.title 갱신, 상단 탭 활성 상태 갱신, history pushState/popstate 처리.
   · 실패/리다이렉트/구형 브라우저 등은 일반 전체 이동으로 안전하게 폴백한다.

   가로채지 않는 것: data-no-partial(기존 Admin·로그아웃), 외부 링크,
   새 탭/수정키 클릭, /admin/home 밖 링크(제품 수정 등 → 기존 admin).
   폼(POST)은 가로채지 않는다(카테고리 CRUD 는 기존대로 제출·리다이렉트).
   ============================================================= */
(function () {
  "use strict";

  // 지원 환경이 아니면 아무것도 하지 않는다(링크가 일반 동작으로 그대로 작동).
  if (!window.fetch || !window.history || !window.history.pushState) return;

  var PREFIX = "/admin/home/";

  function container() {
    return document.getElementById("ah-content");
  }

  function isInternalLink(a) {
    if (!a) return false;
    if (a.hasAttribute("data-no-partial")) return false;
    if (a.target && a.target !== "" && a.target !== "_self") return false;
    if (a.hasAttribute("download")) return false;
    var href = a.getAttribute("href");
    if (!href) return false;
    // 절대경로 내부 링크만 대상 (host 다르면 제외)
    if (a.origin && a.origin !== window.location.origin) return false;
    return href.indexOf(PREFIX) === 0;
  }

  // innerHTML 으로 삽입된 <script> 는 실행되지 않으므로 새 요소로 교체해 재실행한다.
  function runScripts(root) {
    root.querySelectorAll("script").forEach(function (old) {
      var s = document.createElement("script");
      for (var i = 0; i < old.attributes.length; i++) {
        s.setAttribute(old.attributes[i].name, old.attributes[i].value);
      }
      if (!old.src) s.textContent = old.textContent;
      old.parentNode.replaceChild(s, old);
    });
  }

  // 좌측 사이드바(#ah-sidebar)의 활성 메뉴만 갱신한다(부분 로딩 후에도 유지되는 셸).
  function updateSidebarActive(path) {
    var nav = document.getElementById("ah-sidebar");
    if (!nav) return;
    nav.querySelectorAll(".ah-sidebar__item").forEach(function (item) {
      var href = item.getAttribute("href");
      if (!href || href.indexOf(PREFIX.slice(0, -1)) !== 0) {
        // /admin/home 밖(기존 Admin 등)은 활성 대상 아님
        item.classList.remove("is-active");
        return;
      }
      var active =
        href === path || (href !== PREFIX && path.indexOf(href) === 0);
      item.classList.toggle("is-active", active);
    });
  }

  // 토프바(지속 셸)의 페이지 타이틀/액션을 응답 fragment 의 마커로 갱신한다.
  function updateTopbar(frag) {
    var titleMarker = frag.querySelector("[data-ah-topbar-title]");
    var titleEl = document.getElementById("ah-topbar-title");
    if (titleMarker && titleEl) {
      titleEl.textContent =
        titleMarker.getAttribute("data-ah-topbar-title") || "";
    }
    var actionsMarker = frag.querySelector("[data-ah-topbar-actions]");
    var actionsEl = document.getElementById("ah-topbar-actions");
    if (actionsEl) {
      actionsEl.innerHTML = actionsMarker ? actionsMarker.innerHTML : "";
    }
  }

  // 중첩 부분 교체 시, 유지되는 서브내비의 활성 탭을 응답(fragment)의 값과 맞춘다.
  function syncSubnavActive(fragment) {
    var curNav = document.querySelector("#ah-content .ah-subnav");
    var newNav = fragment.querySelector(".ah-subnav");
    if (!curNav || !newNav) return;
    var activeHref = null;
    newNav.querySelectorAll(".glass-nav__item").forEach(function (i) {
      if (i.classList.contains("is-active")) activeHref = i.getAttribute("href");
    });
    curNav.querySelectorAll(".glass-nav__item").forEach(function (i) {
      i.classList.toggle("is-active", i.getAttribute("href") === activeHref);
    });
  }

  function swap(html, url) {
    var host = container();
    if (!host) {
      window.location.href = url;
      return;
    }

    // 응답을 임시 파싱해 중첩 영역(#ah-subcontent) 존재 여부로 교체 범위를 정한다.
    var frag = document.createElement("div");
    frag.innerHTML = html;

    var curSub = document.getElementById("ah-subcontent");
    var newSub = frag.querySelector("#ah-subcontent");

    if (curSub && newSub) {
      // 중첩 부분 교체 — 서브내비/상단 바는 유지하고 그 아래 영역만 바꾼다.
      curSub.innerHTML = newSub.innerHTML;
      runScripts(curSub);
      syncSubnavActive(frag);
    } else {
      // 일반 부분 교체 — #ah-content 전체를 바꾼다.
      host.innerHTML = html;
      runScripts(host);
    }

    // 제목 갱신 (제목 마커는 fragment 최상단에 있음)
    var titleMarker = frag.querySelector("[data-ah-title]");
    if (titleMarker) {
      document.title = titleMarker.getAttribute("data-ah-title") || document.title;
    }

    // 토프바 페이지 타이틀/액션 갱신 (지속 셸)
    updateTopbar(frag);

    // 사이드바 활성 메뉴 갱신 (경로 기준)
    updateSidebarActive(url.split("?")[0].split("#")[0]);

    // 디자인 시스템 재초기화(reveal 등장, nav 인디케이터/서브내비 배선)
    document.dispatchEvent(new CustomEvent("ah:content-loaded"));

    // 콘텐츠 상단으로 스크롤
    window.scrollTo(0, 0);
  }

  function navigate(url, push) {
    fetch(url, {
      headers: { "X-Partial-Nav": "1" },
      credentials: "same-origin",
    })
      .then(function (res) {
        // 인증 만료 등으로 리다이렉트되면 전체 이동으로 폴백(로그인 화면 정상 표시)
        if (res.redirected) {
          window.location.href = url;
          return null;
        }
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.text();
      })
      .then(function (html) {
        if (html === null) return;
        if (push) history.pushState({ ahPartial: true }, "", url);
        swap(html, url);
      })
      .catch(function () {
        // 네트워크/파싱 실패 → 일반 전체 이동
        window.location.href = url;
      });
  }

  // 링크 클릭 가로채기 (이벤트 위임)
  document.addEventListener("click", function (e) {
    if (e.defaultPrevented) return;
    if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) {
      return;
    }
    var a = e.target.closest ? e.target.closest("a") : null;
    if (!isInternalLink(a)) return;

    var href = a.getAttribute("href");
    // 현재 경로와 동일하면 재요청하지 않는다.
    if (href === window.location.pathname) {
      e.preventDefault();
      return;
    }
    e.preventDefault();
    navigate(href, true);
  });

  // 뒤/앞으로 가기 — 부분 로딩으로 되돌린다.
  window.addEventListener("popstate", function (e) {
    if (!e.state || !e.state.ahPartial) return;
    navigate(window.location.pathname + window.location.search, false);
  });

  // 첫 로드 상태를 history 에 심어 popstate 가 올바르게 동작하도록 한다.
  if (!history.state || !history.state.ahPartial) {
    history.replaceState({ ahPartial: true }, "", window.location.href);
  }
})();
