let ymapsLoadPromise: Promise<any> | null = null

export async function loadYmaps(apiKey: string): Promise<any> {
  if ((window as any).ymaps) {
    return new Promise((resolve) => {
      ;(window as any).ymaps.ready(() => resolve((window as any).ymaps))
    })
  }

  if (ymapsLoadPromise) {
    return ymapsLoadPromise
  }

  ymapsLoadPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = `https://api-maps.yandex.ru/2.1/?apikey=${apiKey}&lang=ru_RU`
    script.async = true
    script.onload = () => {
      ;(window as any).ymaps.ready(() => resolve((window as any).ymaps))
    }
    script.onerror = () => {
      ymapsLoadPromise = null
      reject(new Error('Не удалось загрузить скрипт Яндекс Карт'))
    }
    document.head.appendChild(script)
  })

  return ymapsLoadPromise
}
