import { cn } from "@/lib/utils"
import { ButtonHTMLAttributes, forwardRef } from "react"

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost"
  size?: "sm" | "md" | "lg"
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", children, disabled, ...props }, ref) => {
    return (
      <button
        ref={ref}
        disabled={disabled}
        className={cn(
          "inline-flex items-center justify-center rounded-xl font-semibold transition-all",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          {
            "bg-gold text-black hover:bg-gold-dark": variant === "primary",
            "bg-transparent border border-border text-white hover:border-gold hover:text-gold": variant === "secondary",
            "bg-transparent border border-gold text-gold hover:bg-gold hover:text-black": variant === "outline",
            "bg-transparent text-gray-400 hover:text-white hover:bg-white/5": variant === "ghost",
          },
          {
            "px-4 py-2 text-sm": size === "sm",
            "px-6 py-3 text-base": size === "md",
            "px-8 py-4 text-lg": size === "lg",
          },
          className
        )}
        {...props}
      >
        {children}
      </button>
    )
  }
)

Button.displayName = "Button"

export { Button }
