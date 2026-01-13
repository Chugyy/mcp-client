# ============================================
# DOKPLOY CONFIGURATION REQUISE
# ============================================
# Mounts:
#   - Type: Volume mount
#   - Name: uploads_data
#   - Container path: /app/uploads
#
# Environment variables:
#   - APP_NAME="Personal Dashboard API"
#   - DEBUG=false
#   - HOST=0.0.0.0
#   - PORT=8000
#   - JWT_SECRET_KEY (générer avec: openssl rand -hex 32)
#   - JWT_ALGORITHM=HS256
#   - JWT_EXPIRATION_HOURS=24
#   - ADMIN_TOKEN (générer avec: openssl rand -hex 32)
#   - PRODUCTION=true
#   - DB_HOST=postgres
#   - DB_PORT=5432
#   - DB_NAME=personal_dashboard
#   - DB_USER=<user>
#   - DB_PASSWORD=<password>
#   - CORS_ORIGINS=https://your-frontend.com
#   - ANTHROPIC_API_KEY=<key>
#   - ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
#   - OPENAI_API_KEY=<key-optional>
#   - OPENAI_MODEL=gpt-4o
#   - LLM_MAX_TOKENS=1000
#   - LLM_TEMPERATURE=0.7
#   - SUMMARIZATION_PROVIDER=anthropic
#   - TRANSCRIPTION_MODE_DEFAULT=api
#   - EMAIL_USERNAME=<email>
#   - EMAIL_PASSWORD=<password>
#   - EMAIL_SENDER_NAME=<name>
#   - EMAIL_SMTP_HOST=<host>
#   - EMAIL_SMTP_PORT=465
#   - EMAIL_IMAP_HOST=<host>
#   - EMAIL_IMAP_PORT=993
#   - STRIPE_SECRET_KEY=sk_test_<key>
#   - STRIPE_PUBLISHABLE_KEY=pk_test_<key>
#   - STRIPE_WEBHOOK_SECRET=whsec_<key>
#   - STRIPE_PAYMENT_LINK=<url>
#   - STRIPE_PAYMENT_LINK_STANDARD=<url>
#   - STRIPE_PAYMENT_LINK_PREMIUM=<url>
#   - STRIPE_CUSTOMER_PORTAL_URL=<url>
#   - GOOGLE_CLIENT_ID=<id>
#   - GOOGLE_CLIENT_SECRET=<secret>
#   - GOOGLE_REDIRECT_URI=<uri>
#   - FRONTEND_URL=https://your-frontend.com
#   - ENCRYPTION_MASTER_KEY (générer avec: openssl rand -hex 32)
#   - API_URL=https://your-api.com
#   - OAUTH_CLIENT_ID=mcp-client
#   - OAUTH_METADATA_CACHE_TTL=3600
#   - EMBEDDING_MODEL=text-embedding-3-large
#   - EMBEDDING_DIM=3072
#   - CHUNK_SIZE=1000
#   - CHUNK_OVERLAP=200
#
# Ports:
#   - Container: 8000
#   - Public: Yes
# ============================================

FROM python:3.13.1-slim

# Installer dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Créer user non-root
RUN useradd -m -u 1000 appuser

# Définir workdir
WORKDIR /app

# Copier requirements
COPY config/requirements.txt ./config/requirements.txt

# Installer dépendances Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r config/requirements.txt

# Créer dossier uploads avec bonnes permissions
RUN mkdir -p /app/uploads && \
    chown -R appuser:appuser /app/uploads && \
    touch /app/app.log && \
    chown appuser:appuser /app/app.log

# Copier code source
COPY --chown=appuser:appuser . .

# Changer vers user non-root
USER appuser

# Exposer port
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Mode production : uvicorn avec workers (pas de hot-reload)
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
