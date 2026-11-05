# ==============================================================================
# VOCARA FRONTEND PRODUCTION DOCKERFILE (MULTI-STAGE BUILD)
# ==============================================================================

# Stage 1: Build React SPA
FROM node:20-alpine AS builder

WORKDIR /app

# Install build dependencies
COPY package*.json ./
RUN npm ci || npm install

# Copy source files and compile
COPY . .
RUN npm run build

# Stage 2: Production Nginx Runtime
FROM nginx:1.25-alpine

LABEL maintainer="Vocara Engineering Team"
LABEL description="Vocara Production Web Console & Reverse Proxy"

# Clean default static files
RUN rm -rf /usr/share/nginx/html/*

# Copy compiled build output
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy Nginx gateway configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose standard HTTP port
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
