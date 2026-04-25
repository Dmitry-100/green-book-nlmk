import { describe, expect, it } from 'vitest'
import {
  formatCatalogImportDelta,
  formatCatalogImportFields,
} from './catalogImportFormatting'

describe('catalog import formatting', () => {
  it('renders catalog field names as human-readable labels', () => {
    expect(formatCatalogImportFields(['name_latin', 'category', 'biotopes', 'photo_urls'])).toBe(
      'Латинское название, Категория, Местообитания, Фото'
    )
  })

  it('renders empty values and lists clearly', () => {
    expect(
      formatCatalogImportDelta({
        name_latin: 'Acer platanoides',
        conservation_status: null,
        photo_urls: ['https://example.com/a.jpg', 'https://example.com/b.jpg'],
      })
    ).toBe(
      'Латинское название: Acer platanoides | Охранный статус: пусто | Фото: https://example.com/a.jpg; https://example.com/b.jpg'
    )
  })

  it('renders an empty delta as a dash', () => {
    expect(formatCatalogImportDelta({})).toBe('—')
  })
})
