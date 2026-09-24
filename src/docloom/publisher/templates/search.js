(function () {
  var input = document.getElementById("docloom-search");
  var box = document.getElementById("docloom-results");
  var menu = document.getElementById("docloom-menu");
  var theme = document.getElementById("docloom-theme");
  if (theme) {
    theme.addEventListener("click", function () {
      var next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
      if (next === "light") {
        document.documentElement.removeAttribute("data-theme");
        localStorage.removeItem("docloom-theme");
      } else {
        document.documentElement.setAttribute("data-theme", "dark");
        localStorage.setItem("docloom-theme", "dark");
      }
    });
  }
  if (menu) {
    menu.addEventListener("click", function () {
      document.body.classList.toggle("nav-open");
    });
  }
  if (!input || !box || !window.DOCLOOM_SEARCH) {
    return;
  }
  var index = null;
  function esc(value) {
    return String(value).replace(/[&<>"']/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch];
    });
  }
  function load() {
    if (index) {
      return Promise.resolve(index);
    }
    return fetch(window.DOCLOOM_SEARCH).then(function (response) {
      if (!response.ok) {
        throw new Error("search index");
      }
      return response.json();
    }).then(function (data) {
      index = data;
      return data;
    });
  }
  function render(query) {
    var needle = query.trim().toLowerCase();
    if (needle.length < 2 || !index) {
      box.hidden = true;
      box.innerHTML = "";
      return;
    }
    var hits = [];
    for (var i = 0; i < index.length; i += 1) {
      var item = index[i];
      var hay = (item.title + " " + (item.body || "")).toLowerCase();
      if (hay.indexOf(needle) !== -1) {
        hits.push(item);
      }
      if (hits.length === 8) {
        break;
      }
    }
    if (!hits.length) {
      box.hidden = false;
      box.innerHTML = "<p class=\"empty\">Ничего не найдено</p>";
      return;
    }
    box.hidden = false;
    var root = window.DOCLOOM_ROOT || "";
    box.innerHTML = hits.map(function (item) {
      return "<a href=\"" + esc(root + item.path) + "\">" + esc(item.title) + "</a>";
    }).join("");
  }
  input.addEventListener("input", function () {
    load().then(function () { render(input.value); }).catch(function () {
      box.hidden = false;
      box.innerHTML = "<p class=\"empty\">Индекс недоступен</p>";
    });
  });
  input.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      box.hidden = true;
    }
  });
  document.addEventListener("click", function (event) {
    if (!box.contains(event.target) && event.target !== input) {
      box.hidden = true;
    }
  });
})();
