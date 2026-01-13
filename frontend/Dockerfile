# ============================================
# DOKPLOY CONFIGURATION REQUISE
# ============================================
# Build arguments (passés au build Docker):
#   - NEXT_PUBLIC_API_URL (URL backend Dokploy, ex: https://backend.example.com)
#     Important: doit être défini comme BUILD ARG dans Dokploy, pas comme ENV VAR
#
# Environment variables (runtime):
#   - NODE_ENV=production
#
# Ports:
#   - Container: 3000
#   - Public: Oui
#
# Mounts: Aucun (application SSR sans persistance)
#
# Commande build Dokploy (exemple):
#   docker build --build-arg NEXT_PUBLIC_API_URL=https://api.example.com -t frontend .
# ============================================

# ==================== STAGE 1 : DEPENDENCIES ====================
FROM node:24.3-alpine AS deps

WORKDIR /app

# Copier package files
COPY package*.json ./

# Installer dépendances de production uniquement
RUN npm install --only=production

# ==================== STAGE 2 : BUILDER ====================
FROM node:24.3-alpine AS builder

WORKDIR /app

# ARG pour recevoir l'URL de l'API au moment du build
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

# Copier package files
COPY package*.json ./

# Installer toutes les dépendances (dev + prod pour le build)
RUN npm install

# Copier code source
COPY . .

# Build Next.js pour production (génère .next/)
# Désactiver télémétrie pendant le build
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ==================== STAGE 3 : RUNNER (PRODUCTION) ====================
FROM node:24.3-alpine AS runner

# Installer curl pour healthchecks
RUN apk add --no-cache curl

WORKDIR /app

# Créer user non-root
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001

# Copier uniquement les fichiers nécessaires depuis les stages précédents
# 1. Dépendances de production ET TypeScript (requis pour next.config.ts)
COPY --from=builder --chown=nextjs:nodejs /app/node_modules ./node_modules

# 2. Build output Next.js
COPY --from=builder --chown=nextjs:nodejs /app/.next ./.next
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

# 3. Configuration Next.js
COPY --from=builder --chown=nextjs:nodejs /app/next.config.ts ./
COPY --from=builder --chown=nextjs:nodejs /app/package.json ./

# Variables d'environnement production
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Port
EXPOSE 3000

# Changer vers user non-root
USER nextjs

# Lancer Next.js en mode production
CMD ["npm", "start"]

# Healthcheck production
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:3000 || exit 1
