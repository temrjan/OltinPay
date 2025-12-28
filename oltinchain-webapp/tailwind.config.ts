import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        gold: {
          DEFAULT: '#D4AF37',
          light: '#F4D03F',
          dark: '#B8860B',
        },
        background: '#07070a',
        card: '#0c0c12',
        border: '#1e1e2a',
      },
    },
  },
  plugins: [],
}
export default config
