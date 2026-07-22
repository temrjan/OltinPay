# Multi-stage build for the OltinChain Console (Next.js). A server runtime is
# required — the bank route handlers sign requests server-side (E2), so this is
# not a static export. Vercel is the primary deploy target; this Dockerfile is
# for self-hosting. (Not built by CI — verify a `docker build` before relying on
# it; the console.yml gate covers typecheck/lint/test/build.)
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
COPY --from=build /app/package.json ./package.json
COPY --from=build /app/next.config.ts ./next.config.ts
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/.next ./.next
EXPOSE 3000
CMD ["npm", "start"]
