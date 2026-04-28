import api from '../api/client'

type MediaApiClient = {
  get: (url: string, config: { responseType: 'blob' }) => Promise<{ data: Blob }>
}

type ResolvePreviewOptions = {
  s3Key: string
  status: string
  apiClient?: MediaApiClient
  createObjectURL?: (blob: Blob) => string
}

export function buildObservationMediaUrl(s3Key: string): string {
  return `/api/media/${s3Key.split('/').map(encodeURIComponent).join('/')}`
}

export async function resolveObservationMediaPreviewUrl({
  s3Key,
  status,
  apiClient = api,
  createObjectURL = URL.createObjectURL,
}: ResolvePreviewOptions): Promise<string> {
  if (status === 'confirmed') {
    return buildObservationMediaUrl(s3Key)
  }

  const mediaPath = buildObservationMediaUrl(s3Key).replace(/^\/api/, '')
  const { data } = await apiClient.get(mediaPath, { responseType: 'blob' })
  return createObjectURL(data)
}

export function revokeObservationMediaPreviewUrl(
  url: string | null | undefined,
  revokeObjectURL = URL.revokeObjectURL
): void {
  if (url?.startsWith('blob:')) {
    revokeObjectURL(url)
  }
}
