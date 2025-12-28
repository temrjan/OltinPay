'use client'

import { QRCodeSVG } from 'qrcode.react'
import { cn } from '@/lib/utils'

interface QRCodeProps {
  value: string
  size?: number
  className?: string
  includeMargin?: boolean
  bgColor?: string
  fgColor?: string
}

export function QRCode({
  value,
  size = 128,
  className,
  includeMargin = true,
  bgColor = '#FFFFFF',
  fgColor = '#000000',
}: QRCodeProps) {
  if (!value) {
    return null
  }

  return (
    <div
      className={cn(
        'inline-flex items-center justify-center bg-white rounded-xl p-3',
        className
      )}
    >
      <QRCodeSVG
        value={value}
        size={size}
        bgColor={bgColor}
        fgColor={fgColor}
        includeMargin={includeMargin}
        level="M"
      />
    </div>
  )
}

interface WalletQRCodeProps {
  address: string
  size?: number
  className?: string
}

export function WalletQRCode({ address, size = 160, className }: WalletQRCodeProps) {
  if (!address) {
    return null
  }

  // Create Ethereum URI for wallet apps
  const ethereumUri = `ethereum:${address}`

  return (
    <div className={cn('flex flex-col items-center gap-3', className)}>
      <QRCode value={ethereumUri} size={size} />
      <p className="text-xs text-muted text-center max-w-[200px]">
        Отсканируйте для получения OLTIN
      </p>
    </div>
  )
}
