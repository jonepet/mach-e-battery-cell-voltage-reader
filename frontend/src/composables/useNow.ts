import { onMounted, onUnmounted, ref } from 'vue';

export function useNow(intervalMs: number) {
  const now = ref(Date.now());
  let timer: number | undefined;

  onMounted(() => {
    timer = window.setInterval(() => {
      now.value = Date.now();
    }, intervalMs);
  });
  onUnmounted(() => {
    window.clearInterval(timer);
  });

  return now;
}
