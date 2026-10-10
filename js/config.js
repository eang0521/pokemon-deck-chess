/* Where the online room server lives.
   - ?server=wss://host on the page URL overrides it (and is remembered in this browser)
   - when the site itself is served by the Node room server (localhost), rooms are on the same host
   - otherwise PAC_SERVER_URL below: set it to the deployed room server */
(function () {
  const PAC_SERVER_URL = 'wss://pac-rooms.eang0521.workers.dev';
  let url = PAC_SERVER_URL;
  try {
    const q = new URLSearchParams(location.search).get('server');
    if (q) { localStorage.setItem('pac-server', q); url = q; }
    else if (localStorage.getItem('pac-server')) url = localStorage.getItem('pac-server');
    else if (/^(localhost|127\.0\.0\.1)$/.test(location.hostname) && location.port === '8787') url = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host;
  } catch (e) { /* storage blocked: use the default */ }
  window.PAC_SERVER = url.replace(/\/+$/, '');
})();
