# PowerPilot frontend
#
# Builds the Vite bundle, then serves the static output from nginx. The runtime
# image contains no Node and no node_modules.

FROM node:22-alpine AS builder

WORKDIR /build

# npm ci needs both files and installs exactly what the lockfile pins.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build


FROM nginx:1.27-alpine AS runtime

COPY --from=builder /build/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
