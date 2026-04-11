import { afterEach, describe, expect, it, vi } from 'vitest'

type MockScript = {
  src: string
  async: boolean
  onload: (() => void) | null
  onerror: (() => void) | null
}

function setupDomMocks() {
  const scripts: MockScript[] = []
  const createElement = vi.fn((tag: string) => {
    if (tag !== 'script') {
      throw new Error(`Unexpected tag: ${tag}`)
    }

    return {
      src: '',
      async: false,
      onload: null,
      onerror: null,
    } as MockScript
  })

  const appendChild = vi.fn((node: MockScript) => {
    scripts.push(node)
  })

  ;(globalThis as any).document = {
    createElement,
    head: { appendChild },
  }

  return { scripts, createElement, appendChild }
}

describe('loadYmaps', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.resetModules()
    delete (globalThis as any).window
    delete (globalThis as any).document
  })

  it('returns existing ymaps instance when already loaded', async () => {
    const ready = vi.fn((cb: () => void) => cb())
    const ymaps = { ready }
    ;(globalThis as any).window = { ymaps }
    const { createElement, appendChild } = setupDomMocks()

    const { loadYmaps } = await import('./ymapsLoader')
    const loaded = await loadYmaps('api-key')

    expect(loaded).toBe(ymaps)
    expect(ready).toHaveBeenCalledTimes(1)
    expect(createElement).not.toHaveBeenCalled()
    expect(appendChild).not.toHaveBeenCalled()
  })

  it('deduplicates concurrent script loads', async () => {
    ;(globalThis as any).window = {}
    const { scripts, appendChild } = setupDomMocks()
    const { loadYmaps } = await import('./ymapsLoader')

    const first = loadYmaps('api-key')
    const second = loadYmaps('api-key')

    expect(appendChild).toHaveBeenCalledTimes(1)
    expect(scripts).toHaveLength(1)
    expect(scripts[0]?.src).toContain('apikey=api-key')

    ;(globalThis as any).window.ymaps = {
      ready: (cb: () => void) => cb(),
    }
    scripts[0]?.onload?.()

    const [firstResult, secondResult] = await Promise.all([first, second])
    expect(firstResult).toBe((globalThis as any).window.ymaps)
    expect(secondResult).toBe((globalThis as any).window.ymaps)
    expect(firstResult).toBe(secondResult)
  })

  it('resets failed load state and retries on next call', async () => {
    ;(globalThis as any).window = {}
    const { scripts, appendChild } = setupDomMocks()
    const { loadYmaps } = await import('./ymapsLoader')

    const firstAttempt = loadYmaps('api-key')
    scripts[0]?.onerror?.()
    await expect(firstAttempt).rejects.toThrow('Не удалось загрузить скрипт Яндекс Карт')
    expect(appendChild).toHaveBeenCalledTimes(1)

    const secondAttempt = loadYmaps('api-key')
    expect(appendChild).toHaveBeenCalledTimes(2)

    ;(globalThis as any).window.ymaps = {
      ready: (cb: () => void) => cb(),
    }
    scripts[1]?.onload?.()
    await expect(secondAttempt).resolves.toBe((globalThis as any).window.ymaps)
  })
})
