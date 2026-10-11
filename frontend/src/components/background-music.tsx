"use client";

import Script from "next/script";
import { useEffect, useRef, useState } from "react";
import { useLanguage } from "@/components/language-provider";
import { createMusicPlayer, musicTracks, type MusicStatus, type YouTubeApi } from "@/lib/background-music";
import "./background-music.css";

export function BackgroundMusic() {
  const { language } = useLanguage();
  const en = language === "en";
  const [enabled, setEnabled] = useState(false);
  const [trackIndex, setTrackIndex] = useState(0);
  const [apiReady, setApiReady] = useState(false);
  const [status, setStatus] = useState<MusicStatus>("loading");
  const host = useRef<HTMLDivElement>(null);
  const track = musicTracks[trackIndex];

  useEffect(() => {
    if (!enabled) return;
    const browser = window as Window & { YT?: YouTubeApi; onYouTubeIframeAPIReady?: () => void };
    const previous = browser.onYouTubeIframeAPIReady;
    const ready = () => { previous?.(); setApiReady(true); };
    browser.onYouTubeIframeAPIReady = ready;
    const timeout = window.setTimeout(() => {
      if (!browser.YT?.Player) setStatus("error");
    }, 15000);
    return () => {
      window.clearTimeout(timeout);
      if (browser.onYouTubeIframeAPIReady === ready) browser.onYouTubeIframeAPIReady = previous;
    };
  }, [enabled]);

  useEffect(() => {
    const api = (window as Window & { YT?: YouTubeApi }).YT;
    if (!enabled || !apiReady || !api || !host.current) return;
    return createMusicPlayer(api, host.current, track, window.location.origin, setStatus);
  }, [enabled, apiReady, track]);

  return (
    <section className="background-music" aria-label={en ? "Background music" : "เพลงประกอบ"}>
      <div className="background-music-controls">
        <label htmlFor="background-music-track">{en ? "Background music" : "เพลงประกอบ"}</label>
        <select id="background-music-track" value={trackIndex} onChange={(event) => {
          setStatus("loading");
          setTrackIndex(Number(event.target.value));
        }}>
          {musicTracks.map((song, index) => <option key={song.videoId} value={index}>{song.title}</option>)}
        </select>
        <button type="button" onClick={() => {
          setStatus("loading");
          setEnabled(!enabled);
        }}>{enabled ? (en ? "Stop music" : "หยุดเพลง") : (en ? "Play music" : "เล่นเพลง")}</button>
        <span>{trackIndex === 0 ? (en ? "Full song · repeat" : "เต็มเพลง · เล่นวน") : (en ? "2:30–2:40 · repeat" : "2:30–2:40 · เล่นวน")}</span>
      </div>
      {enabled && <>
        <Script id="background-music-api" src="https://www.youtube.com/iframe_api" onReady={() => {
          // The bootstrap script loads the player API separately.
          if ((window as Window & { YT?: YouTubeApi }).YT?.Player) setApiReady(true);
        }} onError={() => setStatus("error")} />
        <div className="background-music-player" ref={host} />
        <p role="status">
          {status === "loading" && (en ? "Loading music…" : "กำลังโหลดเพลง…")}
          {(status === "ready" || status === "blocked") && (en ? "Use the player to play, pause or adjust volume." : "ใช้เครื่องเล่นเพื่อเล่น หยุดชั่วคราว หรือปรับเสียง")}
          {status === "error" && (en ? "Music could not load. You can listen on YouTube." : "โหลดเพลงไม่สำเร็จ คุณสามารถฟังบน YouTube ได้")}
          {" "}<a href={`https://www.youtube.com/watch?v=${track.videoId}`} target="_blank" rel="noopener noreferrer">{en ? "Listen on YouTube" : "ฟังบน YouTube"}</a>
        </p>
      </>}
    </section>
  );
}
