FROM node:24-alpine AS builder
WORKDIR /app

# Copy workspace metadata, then forum source.
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml* ./
COPY services/forum ./services/forum

RUN corepack enable && \
    pnpm install --frozen-lockfile && \
    pnpm -F @conclave/forum build

FROM nginx:1.27-alpine
COPY --from=builder /app/services/forum/dist /usr/share/nginx/html
COPY infra/nginx/forum.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
