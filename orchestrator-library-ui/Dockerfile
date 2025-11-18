# Stage 1: Build the Angular app
FROM node:20-alpine3.20 AS builder

WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Copy package files and install dependencies
COPY package.json pnpm-lock.yaml ./
RUN pnpm install

# Copy the rest of the source code
COPY . .

# Build the Angular app
RUN pnpm run build:prod

# Stage 2: Production image with nginx only
FROM nginx:alpine

WORKDIR /usr/share/nginx/html

# Remove default nginx files
RUN rm -rf ./*

# Copy the built Angular app
COPY --from=builder /app/dist/orchestration_library-front/browser ./

# Rename index.csr.html to index.html for nginx
RUN mv index.csr.html index.html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost:80 > /dev/null || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
