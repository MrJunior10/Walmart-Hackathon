"use strict";

// static/script.js
document.addEventListener('DOMContentLoaded', function () {
  // —— Element refs ——  
  var headerBar = document.querySelector('.header');
  var getStartedBtn = document.getElementById('getStarted');
  var formScreen = document.getElementById('form');
  var resultScreen = document.getElementById('result');
  var regionIn = document.getElementById('region');
  var mediumIn = document.getElementById('medium');
  var categoryIn = document.getElementById('category');
  var heroImg = document.getElementById('heroImg');
  var captionEl = document.getElementById('caption');
  var shopBtn = document.getElementById('shopNow'); // —— Init state ——  

  formScreen.classList.remove('active');
  resultScreen.classList.remove('active'); // —— Get Started → Show Form ——  

  getStartedBtn.addEventListener('click', function () {
    headerBar.style.display = 'none';
    formScreen.classList.add('active');
  }); // —— Autofill Region via IP ——  

  fetch('https://ipapi.co/json/').then(function (r) {
    return r.json();
  }).then(function (d) {
    if (d.region) regionIn.value = d.region;
  })["catch"](function () {
    /* ignore */
  }); // —— Generate → Call Backend & Show Result ——  

  document.getElementById('generate').addEventListener('click', function _callee() {
    var region, medium, category, res, json;
    return regeneratorRuntime.async(function _callee$(_context) {
      while (1) {
        switch (_context.prev = _context.next) {
          case 0:
            region = regionIn.value.trim();
            medium = mediumIn.value.trim();
            category = categoryIn.value.trim();

            if (!(!region || !medium || !category)) {
              _context.next = 5;
              break;
            }

            return _context.abrupt("return", alert('Please fill out all fields.'));

          case 5:
            // swap screens
            formScreen.classList.remove('active');
            resultScreen.classList.add('active');
            captionEl.textContent = 'Generating…';
            _context.prev = 8;
            _context.next = 11;
            return regeneratorRuntime.awrap(fetch('/generate_landing', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json'
              },
              body: JSON.stringify({
                region: region,
                medium: medium,
                category: category
              })
            }));

          case 11:
            res = _context.sent;
            _context.next = 14;
            return regeneratorRuntime.awrap(res.json());

          case 14:
            json = _context.sent;

            if (res.ok) {
              _context.next = 17;
              break;
            }

            throw new Error(json.error || 'API error');

          case 17:
            // populate
            heroImg.src = "/images/".concat(json.modules.hero);
            captionEl.textContent = json.caption || 'Welcome!';

            shopBtn.onclick = function () {
              // map `promo.jpg` → `promo.html`
              var page = json.modules.hero.replace('.jpg', '') + '.html';
              window.location.href = page;
            };

            _context.next = 26;
            break;

          case 22:
            _context.prev = 22;
            _context.t0 = _context["catch"](8);
            console.error(_context.t0);
            captionEl.textContent = 'Oops—something went wrong.';

          case 26:
          case "end":
            return _context.stop();
        }
      }
    }, null, null, [[8, 22]]);
  });
});
//# sourceMappingURL=script.dev.js.map
