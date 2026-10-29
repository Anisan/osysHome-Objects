/* Property history badge menu (fixed, body portal; avoids table-responsive clip). */
(function () {
  "use strict";

  var openMenu = null;
  var openToggle = null;

  function restoreMenu(menu) {
    if (!menu || !menu._phHome) return;
    if (menu.parentElement !== menu._phHome) {
      menu._phHome.appendChild(menu);
    }
    menu._phHome = null;
  }

  function closeMenu() {
    if (openMenu) {
      openMenu.classList.remove("is-open");
      openMenu.style.left = "";
      openMenu.style.top = "";
      restoreMenu(openMenu);
      openMenu = null;
    }
    if (openToggle) {
      openToggle.classList.remove("is-open");
      openToggle.setAttribute("aria-expanded", "false");
      openToggle = null;
    }
  }

  function placeMenu(toggle, menu) {
    var rect = toggle.getBoundingClientRect();
    menu.style.visibility = "hidden";
    menu.classList.add("is-open");
    var w = menu.offsetWidth || 180;
    var h = menu.offsetHeight || 120;
    var left = rect.right - w;
    var top = rect.bottom + 2;
    if (left < 8) left = 8;
    if (left + w > window.innerWidth - 8) left = Math.max(8, window.innerWidth - w - 8);
    if (top + h > window.innerHeight - 8) top = Math.max(8, rect.top - h - 2);
    menu.style.left = left + "px";
    menu.style.top = top + "px";
    menu.style.visibility = "";
  }

  window.__phToggleMenu = function (event, toggle) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    if (!toggle) return;
    var root = toggle.closest(".property-history-dropdown");
    if (!root) return;
    var menu = root.querySelector(".property-history-menu");
    if (!menu) return;

    if (openToggle === toggle && openMenu === menu) {
      closeMenu();
      return;
    }
    closeMenu();
    openMenu = menu;
    openToggle = toggle;
    toggle.classList.add("is-open");
    toggle.setAttribute("aria-expanded", "true");
    menu._phHome = root;
    document.body.appendChild(menu);
    placeMenu(toggle, menu);
  };

  document.addEventListener("click", function (event) {
    if (event.target.closest("[data-ph-toggle]")) return;
    if (event.target.closest(".property-history-menu")) {
      setTimeout(closeMenu, 0);
      return;
    }
    closeMenu();
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") closeMenu();
  });

  window.addEventListener("scroll", closeMenu, true);
  window.addEventListener("resize", closeMenu);
})();
