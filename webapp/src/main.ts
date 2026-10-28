import { createApp } from 'vue'

import App from './App.vue'
import { vJelly } from './jelly'
import { vReflect } from './reflect'
import { router } from './router'
import { enableSquishSwitches } from './squish'
import { applyTheme } from './stores/theme'
import './styles.css'
import { setupTelegram } from './telegram'

setupTelegram()
applyTheme()
enableSquishSwitches()
createApp(App).use(router).directive('jelly', vJelly).directive('reflect', vReflect).mount('#app')
