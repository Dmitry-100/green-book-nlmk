export interface SpeciesEditorialSource {
  season_info?: string | null
  biotopes?: string | null
  do_dont_rules?: string | null
}

export interface SpeciesEditorialSection {
  key: 'habitat' | 'season' | 'care'
  eyebrow: string
  title: string
  body: string
}

function cleanText(value: string | null | undefined): string | null {
  if (!value) return null
  const normalized = value.trim()
  return normalized || null
}

export function buildSpeciesEditorialSections(
  species: SpeciesEditorialSource
): SpeciesEditorialSection[] {
  const sections: SpeciesEditorialSection[] = []
  const biotopes = cleanText(species.biotopes)
  const season = cleanText(species.season_info)
  const rules = cleanText(species.do_dont_rules)

  if (biotopes) {
    sections.push({
      key: 'habitat',
      eyebrow: 'Местообитания',
      title: 'Где искать',
      body: biotopes,
    })
  }
  if (season) {
    sections.push({
      key: 'season',
      eyebrow: 'Сезонность',
      title: 'Когда наблюдать',
      body: season,
    })
  }
  if (rules) {
    sections.push({
      key: 'care',
      eyebrow: 'Памятка',
      title: 'Как действовать',
      body: rules,
    })
  }

  return sections
}
