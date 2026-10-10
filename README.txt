PAC Digital - Pokemon Auto Chess board game (prototype, personal use)

HOW TO PLAY
  Solo / pass & play: open index.html (works offline in any modern browser), or the hosted site.
  1-8 people play; bots with different personalities fill the empty seats. 12 rounds, animated duels.
  - Solo: you against 7 bots.
  - Pass & play: 2-8 people share one device; the screen asks you to hand it over on each turn.
  - Online: everyone on their own device. "Create room" gives a 4-letter code (and a share link);
    others "Join" with it, the host picks a shop turn time limit and starts. If someone disconnects,
    a bot plays their seat until they come back ("Rejoin" on the title screen).
  Tips: Hint button suggests a move; Auto lineup fills your lineup; shift-click buys quickly;
  local games autosave (Continue on title screen). Settings & Rules are in the header.

CODE
  js/engine.js  duel engine (port of the Python sim in tools/pac-sim)
  js/game.js    rules: decks, shop, picks, battles, scoring; any seat can be human or bot
  js/bots.js    bot personalities (PERSONAS)
  js/flow.js    table flow shared by browser and server: actions, bot steps, per-seat views
  js/ui_*.js    screens; js/net.js online rooms; js/config.js which room server to use
  server/       online room server: room.js (logic), node.js (Node host), worker.js (Cloudflare)
  tests/        node tests/flow_test.js, node tests/room_test.js, node tests/net_test.js ws://host
  tools/        data / print / rulebook build pipeline (see tools/README.md)

ONLINE SERVER
  Local play-testing: cd server && npm install && npm start, then open http://localhost:8787
  (serves the site and the rooms; open it in several tabs or on other devices on your network).
  Production (Cloudflare Workers + Durable Objects, free tier is enough):
    cd server && npx wrangler login && npm run deploy
  (deployed: wss://pac-rooms.pac-rooms.workers.dev). A new deploy elsewhere prints its address: put it in js/config.js
  (PAC_SERVER_URL) and redeploy the site. Any page also accepts ?server=wss://... to override it.
