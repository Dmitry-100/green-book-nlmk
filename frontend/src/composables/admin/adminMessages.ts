export type AdminMessages = {
  success: (message: string) => unknown
  error: (message: string) => unknown
  warning: (message: string) => unknown
  info: (message: string) => unknown
}

const TOAST_CONTAINER_ID = 'greenbook-admin-toasts'
const TOAST_STYLE_ID = 'greenbook-admin-toast-styles'

function ensureToastStyles() {
  if (typeof document === 'undefined' || document.getElementById(TOAST_STYLE_ID)) {
    return
  }

  const style = document.createElement('style')
  style.id = TOAST_STYLE_ID
  style.textContent = `
    #${TOAST_CONTAINER_ID} {
      position: fixed;
      right: 18px;
      top: 18px;
      z-index: 3000;
      display: grid;
      gap: 10px;
      max-width: min(360px, calc(100vw - 32px));
      pointer-events: none;
    }
    .admin-toast {
      border-radius: 8px;
      box-shadow: 0 12px 28px rgba(15, 23, 42, 0.18);
      color: #fff;
      font-size: 14px;
      font-weight: 700;
      line-height: 1.35;
      padding: 12px 14px;
      pointer-events: auto;
      transition: opacity 0.18s ease, transform 0.18s ease;
    }
    .admin-toast--success { background: #2f7d62; }
    .admin-toast--error { background: #b42318; }
    .admin-toast--warning { background: #a16207; }
    .admin-toast--info { background: #2563eb; }
    .admin-toast--leaving {
      opacity: 0;
      transform: translateY(-6px);
    }
  `
  document.head.appendChild(style)
}

function ensureToastContainer() {
  if (typeof document === 'undefined') {
    return null
  }
  ensureToastStyles()
  const existing = document.getElementById(TOAST_CONTAINER_ID)
  if (existing) {
    return existing
  }
  const container = document.createElement('div')
  container.id = TOAST_CONTAINER_ID
  document.body.appendChild(container)
  return container
}

function showAdminMessage(kind: keyof AdminMessages, message: string) {
  const container = ensureToastContainer()
  if (!container) {
    return
  }

  const toast = document.createElement('div')
  toast.className = `admin-toast admin-toast--${kind}`
  toast.textContent = message
  toast.setAttribute('role', kind === 'error' ? 'alert' : 'status')
  container.appendChild(toast)
  window.setTimeout(() => {
    toast.classList.add('admin-toast--leaving')
    window.setTimeout(() => toast.remove(), 180)
  }, 3600)
}

export const defaultAdminMessages: AdminMessages = {
  success: (message: string) => {
    showAdminMessage('success', message)
  },
  error: (message: string) => {
    showAdminMessage('error', message)
  },
  warning: (message: string) => {
    showAdminMessage('warning', message)
  },
  info: (message: string) => {
    showAdminMessage('info', message)
  },
}
