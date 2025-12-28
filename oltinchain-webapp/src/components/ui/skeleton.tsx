import { cn } from '@/lib/utils'

interface SkeletonProps {
  className?: string
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        'animate-pulse rounded-lg bg-white/5',
        className
      )}
    />
  )
}

export function BalanceSkeleton() {
  return (
    <div className="bg-card border border-border rounded-2xl p-4 space-y-4">
      <div className="flex justify-between items-start">
        <div className="space-y-2">
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-7 w-32" />
        </div>
        <div className="space-y-2 text-right">
          <Skeleton className="h-3 w-20 ml-auto" />
          <Skeleton className="h-7 w-28" />
        </div>
      </div>
      <div className="border-t border-border pt-3 space-y-2">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-8 w-full" />
      </div>
    </div>
  )
}

export function PriceSkeleton() {
  return (
    <div className="bg-card border border-border rounded-2xl p-4 space-y-3">
      <Skeleton className="h-4 w-32" />
      <div className="flex justify-between">
        <div className="space-y-1">
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-6 w-24" />
        </div>
        <div className="space-y-1 text-right">
          <Skeleton className="h-3 w-16 ml-auto" />
          <Skeleton className="h-6 w-24" />
        </div>
      </div>
    </div>
  )
}

export function TransactionSkeleton() {
  return (
    <div className="bg-card border border-border rounded-2xl p-3 space-y-2">
      <div className="flex justify-between items-start">
        <div className="space-y-1">
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-3 w-24" />
        </div>
        <div className="space-y-1 text-right">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-3 w-20" />
        </div>
      </div>
    </div>
  )
}

export function TransactionListSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <TransactionSkeleton key={i} />
      ))}
    </div>
  )
}

export function DashboardSkeleton() {
  return (
    <div className="space-y-4 p-4">
      <BalanceSkeleton />
      <PriceSkeleton />
      <div className="grid grid-cols-2 gap-3">
        <Skeleton className="h-12 rounded-xl" />
        <Skeleton className="h-12 rounded-xl" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Skeleton className="h-12 rounded-xl" />
        <Skeleton className="h-12 rounded-xl" />
      </div>
    </div>
  )
}
