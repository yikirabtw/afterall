// Тумблеры .switch «оживают» после первого переключения: класс switch--live включает анимацию
// растяжения (styles.css). Без него анимация проигрывалась бы у всех тумблеров при открытии экрана.
export function enableSquishSwitches(): void {
  document.addEventListener(
    'change',
    (event) => {
      const target = event.target
      if (target instanceof HTMLInputElement && target.classList.contains('switch')) target.classList.add('switch--live')
    },
    true,
  )
}
