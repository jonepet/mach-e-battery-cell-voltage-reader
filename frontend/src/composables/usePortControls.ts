import { onMounted, ref } from 'vue';

import { connectPort, disconnectPort, listPorts } from '../api';

export function usePortControls() {
  const ports = ref<readonly string[]>([]);
  const selected = ref('');
  const notice = ref<string | null>(null);

  async function attempt(action: () => Promise<void>): Promise<void> {
    notice.value = null;
    try {
      await action();
    } catch (error) {
      notice.value = error instanceof Error ? error.message : 'The request failed.';
    }
  }

  const refresh = (): Promise<void> =>
    attempt(async () => {
      ports.value = await listPorts();
      if (!ports.value.includes(selected.value)) {
        selected.value = ports.value[0] ?? '';
      }
    });

  const connect = (): Promise<void> => attempt(() => connectPort(selected.value));
  const disconnect = (): Promise<void> => attempt(disconnectPort);

  onMounted(refresh);

  return { ports, selected, notice, refresh, connect, disconnect };
}
