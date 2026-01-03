// Telegram WebApp types
interface TelegramWebApp {
  initData: string
  initDataUnsafe: {
    query_id?: string
    user?: {
      id: number
      is_bot?: boolean
      first_name: string
      last_name?: string
      username?: string
      language_code?: string
      is_premium?: boolean
    }
    auth_date: number
    hash: string
  }
  version: string
  platform: string
  colorScheme: "light" | "dark"
  themeParams: Record<string, string>
  isExpanded: boolean
  viewportHeight: number
  viewportStableHeight: number
  headerColor: string
  backgroundColor: string
  isClosingConfirmationEnabled: boolean
  ready: () => void
  expand: () => void
  close: () => void
  MainButton: {
    text: string
    color: string
    textColor: string
    isVisible: boolean
    isActive: boolean
    isProgressVisible: boolean
    setText: (text: string) => void
    onClick: (callback: () => void) => void
    offClick: (callback: () => void) => void
    show: () => void
    hide: () => void
    enable: () => void
    disable: () => void
    showProgress: (leaveActive?: boolean) => void
    hideProgress: () => void
  }
  BackButton: {
    isVisible: boolean
    onClick: (callback: () => void) => void
    offClick: (callback: () => void) => void
    show: () => void
    hide: () => void
  }
  HapticFeedback: {
    impactOccurred: (style: "light" | "medium" | "heavy" | "rigid" | "soft") => void
    notificationOccurred: (type: "error" | "success" | "warning") => void
    selectionChanged: () => void
  }
}

declare global {
  interface Window {
    Telegram?: {
      WebApp: TelegramWebApp
    }
  }
}

/**
 * Get Telegram WebApp instance
 */
export function getTelegramWebApp(): TelegramWebApp | null {
  if (typeof window === "undefined") return null
  return window.Telegram?.WebApp || null
}

/**
 * Check if running inside Telegram Mini App
 */
export function isTelegramWebApp(): boolean {
  const tg = getTelegramWebApp()
  return !!tg?.initData
}

/**
 * Get Telegram user data (unsigned, for display only)
 */
export function getTelegramUser() {
  const tg = getTelegramWebApp()
  return tg?.initDataUnsafe?.user || null
}

/**
 * Get initData for backend validation
 * Backend should validate this using bot token
 */
export function getInitData(): string | null {
  const tg = getTelegramWebApp()
  return tg?.initData || null
}

/**
 * Initialize Telegram WebApp
 * Call this on app mount
 */
export function initTelegramWebApp() {
  const tg = getTelegramWebApp()
  if (tg) {
    tg.ready()
    tg.expand()
  }
}

/**
 * Trigger haptic feedback
 */
export function hapticFeedback(
  type: "success" | "error" | "warning" | "light" | "medium" | "heavy"
) {
  const tg = getTelegramWebApp()
  if (!tg?.HapticFeedback) return

  if (type === "success" || type === "error" || type === "warning") {
    tg.HapticFeedback.notificationOccurred(type)
  } else {
    tg.HapticFeedback.impactOccurred(type)
  }
}

/**
 * Close the Mini App
 */
export function closeMiniApp() {
  const tg = getTelegramWebApp()
  tg?.close()
}

/**
 * Show/hide back button
 */
export function showBackButton(callback: () => void) {
  const tg = getTelegramWebApp()
  if (tg?.BackButton) {
    tg.BackButton.onClick(callback)
    tg.BackButton.show()
  }
}

export function hideBackButton() {
  const tg = getTelegramWebApp()
  tg?.BackButton?.hide()
}
