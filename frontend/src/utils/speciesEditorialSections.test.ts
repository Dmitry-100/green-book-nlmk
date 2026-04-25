import { describe, expect, it } from 'vitest'
import { buildSpeciesEditorialSections } from './speciesEditorialSections'

describe('species editorial sections', () => {
  it('builds field guide sections from existing species content', () => {
    expect(
      buildSpeciesEditorialSections({
        season_info: '  апрель-сентябрь  ',
        biotopes: 'Опушки, парки, пойменные луга',
        do_dont_rules: 'Не тревожить гнездо и не брать птенцов в руки',
      })
    ).toEqual([
      {
        key: 'habitat',
        eyebrow: 'Местообитания',
        title: 'Где искать',
        body: 'Опушки, парки, пойменные луга',
      },
      {
        key: 'season',
        eyebrow: 'Сезонность',
        title: 'Когда наблюдать',
        body: 'апрель-сентябрь',
      },
      {
        key: 'care',
        eyebrow: 'Памятка',
        title: 'Как действовать',
        body: 'Не тревожить гнездо и не брать птенцов в руки',
      },
    ])
  })

  it('skips empty field guide sections', () => {
    expect(
      buildSpeciesEditorialSections({
        season_info: '   ',
        biotopes: null,
        do_dont_rules: 'Не собирать плодовые тела',
      })
    ).toEqual([
      {
        key: 'care',
        eyebrow: 'Памятка',
        title: 'Как действовать',
        body: 'Не собирать плодовые тела',
      },
    ])
  })
})
