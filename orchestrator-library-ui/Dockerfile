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
RUN pnpm build

# Stage 2: Setup for SSR
FROM node:20-alpine3.20

WORKDIR /usr/app

# Copy the dist folder from the builder stage
COPY --from=builder /app/dist ./dist

# Copy package.json for potential dependencies
COPY --from=builder /app/package.json ./

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose the port the app runs on
EXPOSE 4000

# Command to run the application
CMD ["node", "dist/orchestration_library-front/server/server.mjs"]
