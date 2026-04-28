import { describe, expect, it, vi } from 'vitest'
import {
  buildObservationMediaUrl,
  resolveObservationMediaPreviewUrl,
  revokeObservationMediaPreviewUrl,
} from './observationMedia'

describe('observation media preview URLs', () => {
  it('uses an authorized blob request for non-public observation media', async () => {
    const blob = new Blob(['image'], { type: 'image/jpeg' })
    const apiClient = {
      get: vi.fn().mockResolvedValue({ data: blob }),
    }
    const createObjectURL = vi.fn().mockReturnValue('blob:private-observation-photo')

    const url = await resolveObservationMediaPreviewUrl({
      s3Key: 'observations/private-photo.jpg',
      status: 'on_review',
      apiClient,
      createObjectURL,
    })

    expect(apiClient.get).toHaveBeenCalledWith(
      '/media/observations/private-photo.jpg',
      { responseType: 'blob' }
    )
    expect(createObjectURL).toHaveBeenCalledWith(blob)
    expect(url).toBe('blob:private-observation-photo')
  })

  it('keeps confirmed observation media as a public URL', async () => {
    const apiClient = { get: vi.fn() }

    const url = await resolveObservationMediaPreviewUrl({
      s3Key: 'observations/public-photo.jpg',
      status: 'confirmed',
      apiClient,
      createObjectURL: vi.fn(),
    })

    expect(apiClient.get).not.toHaveBeenCalled()
    expect(url).toBe('/api/media/observations/public-photo.jpg')
  })

  it('encodes media key path segments safely', () => {
    expect(buildObservationMediaUrl('observations/photo with spaces.jpg')).toBe(
      '/api/media/observations/photo%20with%20spaces.jpg'
    )
  })

  it('revokes only blob preview URLs', () => {
    const revokeObjectURL = vi.fn()

    revokeObservationMediaPreviewUrl('blob:private-observation-photo', revokeObjectURL)
    revokeObservationMediaPreviewUrl('/api/media/observations/public-photo.jpg', revokeObjectURL)

    expect(revokeObjectURL).toHaveBeenCalledTimes(1)
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:private-observation-photo')
  })
})
