// GDPR Cookie Consent — Consent Mode v2
(function () {
  var STORAGE_KEY = 'pa_consent';
  var MEASUREMENT_ID = 'G-K6B2W247ES';

  // Varsayılan: her şey reddedilmiş
  function setDefaultDenied() {
    window.dataLayer = window.dataLayer || [];
    function gtag() { dataLayer.push(arguments); }
    gtag('consent', 'default', {
      analytics_storage: 'denied',
      ad_storage: 'denied',
      ad_user_data: 'denied',
      ad_personalization: 'denied',
      wait_for_update: 500
    });
  }

  function updateConsent(granted) {
    window.dataLayer = window.dataLayer || [];
    function gtag() { dataLayer.push(arguments); }
    var val = granted ? 'granted' : 'denied';
    gtag('consent', 'update', {
      analytics_storage: val,
      ad_storage: 'denied',
      ad_user_data: 'denied',
      ad_personalization: 'denied'
    });
  }

  function saveChoice(granted) {
    try { localStorage.setItem(STORAGE_KEY, granted ? '1' : '0'); } catch (e) {}
  }

  function getChoice() {
    try { return localStorage.getItem(STORAGE_KEY); } catch (e) { return null; }
  }

  function removeBanner() {
    var el = document.getElementById('pa-consent-banner');
    if (el) el.remove();
  }

  function accept() {
    updateConsent(true);
    saveChoice(true);
    removeBanner();
  }

  function decline() {
    updateConsent(false);
    saveChoice(false);
    removeBanner();
  }

  function showBanner() {
    if (document.getElementById('pa-consent-banner')) return;
    var banner = document.createElement('div');
    banner.id = 'pa-consent-banner';
    banner.style.cssText = [
      'position:fixed', 'bottom:16px', 'left:50%', 'transform:translateX(-50%)',
      'z-index:9999', 'width:calc(100% - 32px)', 'max-width:600px',
      'background:#fff', 'border:1px solid #e5e7eb',
      'border-radius:14px', 'padding:16px 20px',
      'box-shadow:0 4px 24px rgba(0,0,0,0.10)',
      'display:flex', 'align-items:center', 'gap:12px',
      'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif',
      'font-size:13px', 'color:#374151', 'line-height:1.5'
    ].join(';');

    banner.innerHTML =
      '<div style="flex:1">' +
        '<strong style="display:block;margin-bottom:2px;color:#111827">Çerez Bildirimi</strong>' +
        'Deneyimi iyileştirmek için anonim analitik veriler topluyoruz. ' +
        '<a href="/gizlilik.html" style="color:#4f46e5;text-decoration:none">Gizlilik politikası</a>' +
      '</div>' +
      '<div style="display:flex;gap:8px;flex-shrink:0">' +
        '<button id="pa-consent-decline" style="padding:7px 14px;border-radius:8px;border:1px solid #d1d5db;background:#fff;color:#6b7280;font-size:12px;cursor:pointer;white-space:nowrap">Reddet</button>' +
        '<button id="pa-consent-accept" style="padding:7px 14px;border-radius:8px;border:none;background:#4f46e5;color:#fff;font-size:12px;font-weight:600;cursor:pointer;white-space:nowrap">Kabul Et</button>' +
      '</div>';

    document.body.appendChild(banner);
    document.getElementById('pa-consent-accept').addEventListener('click', accept);
    document.getElementById('pa-consent-decline').addEventListener('click', decline);
  }

  // Başlat
  setDefaultDenied();

  var choice = getChoice();
  if (choice === '1') {
    updateConsent(true);
  } else if (choice === null) {
    // İlk ziyaret — banner göster
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', showBanner);
    } else {
      showBanner();
    }
  }
  // choice === '0' → reddetti, banner gösterme, varsayılan denied kalır
})();
