import { useEffect, useState } from "react";

// Hash routing works from file:// and needs no server.
export interface Route {
  path: string;
  segments: string[];
  query: URLSearchParams;
}

function parse(hash: string): Route {
  const raw = hash.replace(/^#\/?/, "");
  const [p, q = ""] = raw.split("?");
  const segments = p.split("/").filter(Boolean).map(decodeURIComponent);
  return { path: segments[0] ?? "", segments, query: new URLSearchParams(q) };
}

export function useRoute(): Route {
  const [route, setRoute] = useState(() => parse(window.location.hash));
  useEffect(() => {
    const onHash = () => setRoute(parse(window.location.hash));
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  return route;
}

export function href(...segments: string[]): string {
  return "#/" + segments.map(encodeURIComponent).join("/");
}

export function navigate(...segments: string[]) {
  window.location.hash = href(...segments);
}
