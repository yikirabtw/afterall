import { createApp } from 'vue'

import App from './App.vue'
import { router } from './router'
import './styles.css'
import { setupTelegram } from './telegram'

setupTelegram()
createApp(App).use(router).mount('#app')
