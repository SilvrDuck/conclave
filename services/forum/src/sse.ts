/**
 * SSE hook. Reconnects on close. Calls `onEvent` for every named-event
 * frame; calls `onKeepalive` for the 15s heartbeat.
 */

import { useEffect } from "react";
import { mutate } from "swr";
import { streamUrl } from "./api";

const STATE_KEYS = [
  "/state/pods",
  "/state/proclamations",
  "/state/proposals",
  "/state/councils",
  "/state/decisions",
  "/state/calls",
  "/state/activity",
  "/state/endpoints",
  "/inbox",
];

const EVENT_TYPE_TO_KEYS: Record<string, string[]> = {
  ProclamationIssued: ["/state/proclamations", "/state/activity"],
  ProposalOpened: ["/state/proposals", "/state/activity", "/inbox"],
  ProposalClosed: ["/state/proposals", "/state/decisions", "/state/activity", "/inbox"],
  BallotCast: ["/state/proposals", "/state/activity"],
  CouncilOpened: ["/state/councils", "/state/activity", "/inbox"],
  MessagePosted: ["/state/councils", "/state/activity"],
  CouncilClosed: ["/state/councils", "/state/decisions", "/state/activity"],
  DecisionPlaceholderCreated: ["/state/decisions"],
  DecisionSealed: ["/state/decisions", "/state/activity"],
  PodContainerStarted: ["/state/pods", "/state/activity"],
  PodAdmitted: ["/state/pods", "/state/activity"],
  PodRenamed: ["/state/pods", "/state/activity"],
  PodExited: ["/state/pods", "/state/activity"],
  PodImageSwapped: ["/state/pods", "/state/activity"],
  PodMarkedStuck: ["/state/pods", "/inbox"],
  PodHealthChanged: ["/state/pods"],
  EndpointObserved: ["/state/endpoints"],
};

export function useDomainStream(): void {
  useEffect(() => {
    let es: EventSource | null = null;
    let cancelled = false;

    const connect = () => {
      if (cancelled) return;
      es = new EventSource(streamUrl());
      es.addEventListener("domain", (ev: MessageEvent) => {
        try {
          const data = JSON.parse(ev.data);
          const keys = EVENT_TYPE_TO_KEYS[data.event_type] ?? [];
          // Targeted revalidation, plus the call-graph since most events
          // imply edge changes too.
          for (const k of [...keys, "/state/calls"]) mutate(`/state${k.slice(6)}` === k ? k : k);
          for (const k of keys) mutate(k);
        } catch {
          /* malformed payload - ignore */
        }
      });
      es.onerror = () => {
        es?.close();
        if (!cancelled) setTimeout(connect, 2000);
      };
    };
    connect();
    // Polling fallback while SSE is reconnecting.
    const poll = window.setInterval(() => {
      for (const k of STATE_KEYS) mutate(k);
    }, 5000);
    return () => {
      cancelled = true;
      es?.close();
      window.clearInterval(poll);
    };
  }, []);
}
