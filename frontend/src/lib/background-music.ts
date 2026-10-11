export const musicTracks = [
  { title: "Odysseus", videoId: "WCxx_OVOVUw", startSeconds: 0 },
  { title: "The Trial of the Bow / Vengeance", videoId: "a5IQCGdd_m8", startSeconds: 150, endSeconds: 160 },
] as const;

type Track = { title: string; videoId: string; startSeconds: number; endSeconds?: number };
type Video = { videoId: string; startSeconds: number; endSeconds?: number };
type Player = {
  playVideo(): void;
  setVolume(volume: number): void;
  getCurrentTime(): number;
  getPlayerState(): number;
  loadVideoById(video: Video): void;
  destroy(): void;
};
export type MusicStatus = "loading" | "ready" | "blocked" | "error";
export type YouTubeApi = {
  Player: new (element: HTMLElement, options: {
    videoId: string;
    width: string;
    height: string;
    playerVars: { origin: string; playsinline: number; start: number; end?: number };
    events: {
      onReady(event: { target: Player }): void;
      onStateChange(event: { data: number; target: Player }): void;
      onAutoplayBlocked(): void;
      onError(): void;
    };
  }) => Player;
};

export function createMusicPlayer(api: YouTubeApi, host: HTMLElement, track: Track, origin: string, onStatus: (status: MusicStatus) => void) {
  // YouTube replaces this element; keep React's host intact for cleanup and song switches.
  const mount = document.createElement("div");
  host.appendChild(mount);
  let disposed = false;
  const video: Video = { videoId: track.videoId, startSeconds: track.startSeconds, ...(track.endSeconds === undefined ? {} : { endSeconds: track.endSeconds }) };
  const player = new api.Player(mount, {
    videoId: track.videoId,
    width: "100%",
    height: "240",
    playerVars: { origin, playsinline: 1, start: track.startSeconds, ...(track.endSeconds === undefined ? {} : { end: track.endSeconds }) },
    events: {
      onReady({ target }) {
        if (disposed) return;
        onStatus("ready");
        target.setVolume(25);
        target.playVideo();
      },
      onStateChange({ data, target }) {
        if (disposed) return;
        if (data === 0) target.loadVideoById(video);
        if (data === 1) onStatus("ready");
      },
      onAutoplayBlocked() { if (!disposed) onStatus("blocked"); },
      onError() { if (!disposed) onStatus("error"); },
    },
  });
  // Native seeking can discard YouTube's endSeconds; enforce the segment while playing.
  const end = track.endSeconds;
  const timer = end === undefined ? undefined : window.setInterval(() => {
    if (disposed || player.getPlayerState() !== 1) return;
    const time = player.getCurrentTime();
    if (time < track.startSeconds || time >= end) player.loadVideoById(video);
  }, 250);
  return () => {
    disposed = true;
    window.clearInterval(timer);
    player.destroy();
    host.replaceChildren();
  };
}
