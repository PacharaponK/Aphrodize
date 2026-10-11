import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import ts from "typescript";

const exports = {};
const code = ts.transpileModule(fs.readFileSync("src/lib/background-music.ts", "utf8"), {
  compilerOptions: { module: ts.ModuleKind.CommonJS },
}).outputText;
new Function("exports", code)(exports);
const { createMusicPlayer, musicTracks } = exports;

test("music repeats the requested ranges, respects pause, and cleans up on stop/switch", () => {
  const previousWindow = globalThis.window;
  const previousDocument = globalThis.document;
  let tick;
  let cleared;
  globalThis.window = {
    setInterval(callback, delay) { assert.equal(delay, 250); tick = callback; return 7; },
    clearInterval(timer) { cleared = timer; },
  };
  const mount = {};
  globalThis.document = { createElement() { return mount; } };
  try {
    for (const [index, track] of musicTracks.entries()) {
      tick = undefined;
      let options;
      let destroyed = false;
      let emptied = false;
      let time = 155;
      let state = 1;
      const loads = [];
      const statuses = [];
      const player = {
        playVideo() { this.played = true; },
        setVolume(volume) { this.volume = volume; },
        getCurrentTime() { return time; },
        getPlayerState() { return state; },
        loadVideoById(video) { loads.push(video); },
        destroy() { destroyed = true; },
      };
      const api = { Player: class { constructor(element, config) { assert.equal(element, mount); options = config; return player; } } };
      const host = { appendChild(element) { assert.equal(element, mount); }, replaceChildren() { emptied = true; } };
      const stop = createMusicPlayer(api, host, track, "https://aphrodize.example", (status) => statuses.push(status));
      assert.equal(options.playerVars.origin, "https://aphrodize.example");
      assert.equal(options.videoId, index === 0 ? "WCxx_OVOVUw" : "a5IQCGdd_m8");
      assert.equal(options.playerVars.start, index === 0 ? 0 : 150);
      assert.equal(options.playerVars.end, index === 0 ? undefined : 160);
      options.events.onReady({ target: player });
      assert.equal(player.volume, 25);
      assert.equal(player.played, true);
      options.events.onStateChange({ data: 2, target: player });
      assert.equal(loads.length, 0, "pausing must not restart playback");
      options.events.onStateChange({ data: 0, target: player });
      const expected = index === 0 ? { videoId: track.videoId, startSeconds: 0 } : { videoId: track.videoId, startSeconds: 150, endSeconds: 160 };
      assert.deepEqual(loads.pop(), expected, "ending must reload the full song or bounded segment");
      if (index === 1) {
        tick();
        assert.equal(loads.length, 0);
        time = 160;
        state = 2;
        tick();
        assert.equal(loads.length, 0, "polling must preserve pause");
        state = 1;
        tick();
        assert.deepEqual(loads.pop(), expected, "loop at 2:40");
        time = 10;
        tick();
        assert.deepEqual(loads.pop(), expected, "seeking outside the segment returns to 2:30");
      } else assert.equal(tick, undefined, "full songs do not need polling");
      options.events.onAutoplayBlocked();
      assert.equal(statuses.at(-1), "blocked");
      options.events.onError();
      assert.equal(statuses.at(-1), "error");
      stop();
      assert.ok(destroyed && emptied);
      assert.equal(cleared, index === 0 ? undefined : 7);
      options.events.onStateChange({ data: 0, target: player });
      assert.equal(loads.length, 0, "late callbacks must not restart stopped music");
    }
  } finally {
    globalThis.window = previousWindow;
    globalThis.document = previousDocument;
  }
});
