import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        background: '#0D0D0D',
        card: '#1A1A1A',
        border: '#2A2A2A',
        'text-primary': '#FFFFFF',
        'text-muted': '#8A8A8A',
        green: '#22C55E',
        red: '#EF4444',
        gold: '#F59E0B',
      },
    },
  },
  plugins: [],
};

export default config;
