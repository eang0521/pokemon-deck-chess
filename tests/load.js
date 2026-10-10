// Loads the browser game scripts into Node (they attach to `window`), for tests and the Node room server.
const path = require('path');
function load() {
  if (!global.window) global.window = global;
  const js = f => path.join(__dirname, '..', 'js', f);
  require(js('data.js'));
  const E = require(js('engine.js'));
  const G = require(js('game.js'));
  const B = require(js('bots.js'));
  const Flow = require(js('flow.js'));
  return { E, G, B, Flow };
}
module.exports = { load };
