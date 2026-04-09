# Stage 1: Build the Angular app
FROM node:20-alpine3.20 AS builder

WORKDIR /app

# Increase Node.js memory limit for Angular builds
ENV NODE_OPTIONS="--max-old-space-size=4096"

# Install pnpm
RUN npm install -g pnpm

# Copy package files and install dependencies
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# Copy the rest of the source code
COPY . .

# Build the Angular app with verbose output to track progress
RUN echo "Starting Angular build..." && \
    pnpm run build:prod && \
    echo "Build completed successfully"

# Stage 2: Production image with nginx only
FROM nginx:alpine

WORKDIR /usr/share/nginx/html

# Remove default nginx files
RUN rm -rf ./*

# Copy the built Angular app
COPY --from=builder /app/dist/orchestration_library-front/browser ./

# Rename index.csr.html to index.html for nginx
RUN mv index.csr.html index.html

# Copy nginx templates and runtime entrypoint
COPY conf/proxy.conf.template /etc/nginx/templates/proxy.conf.template
COPY conf/no_proxy.conf /etc/nginx/templates/no_proxy.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost:80 > /dev/null || exit 1

# Start nginx via runtime configuration entrypoint
ENTRYPOINT ["/entrypoint.sh"]
