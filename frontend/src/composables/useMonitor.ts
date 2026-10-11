import { onMounted, onUnmounted, ref, shallowRef } from 'vue';

import { eventsUrl } from '../api';
import type { MonitorState } from '../types';

const RECONNECT_DELAY_MS = 1000;

const NO_STATE: MonitorState = { status: 'disconnected', port: null, adapter: null, reading: null };

export function useMonitor() {
  const state = shallowRef<MonitorState>(NO_STATE);
  const live = ref(false);
  let socket: WebSocket | null = null;
  let retry: number | undefined;

  function open(): void {
    const opened = new WebSocket(eventsUrl());
    socket = opened;
    opened.addEventListener('open', () => {
      live.value = true;
    });
    opened.addEventListener('message', (event) => {
      state.value = JSON.parse(event.data as string) as MonitorState;
    });
    opened.addEventListener('close', () => {
      live.value = false;
      retry = window.setTimeout(open, RECONNECT_DELAY_MS);
    });
  }

  onMounted(open);
  onUnmounted(() => {
    window.clearTimeout(retry);
    socket?.close();
    socket = null;
  });

  return { state, live };
}
