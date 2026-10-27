import { ref } from 'vue'

// Состояние интерфейса, которое должно пережить переход на другой экран и обратно
export const lobbiesTab = ref<'all' | 'mine'>('all')
