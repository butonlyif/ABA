FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
COPY apps/mobile-web/package.json apps/mobile-web/package.json
COPY apps/admin-web/package.json apps/admin-web/package.json
COPY packages/contracts/package.json packages/contracts/package.json
RUN npm install
COPY apps/mobile-web apps/mobile-web
COPY apps/admin-web apps/admin-web
RUN npm --workspace @aba/mobile-web run build && npm --workspace @aba/admin-web run build

FROM nginx:1.27-alpine
COPY apps/mobile-web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/apps/mobile-web/dist /usr/share/nginx/html
COPY --from=build /app/apps/admin-web/dist /usr/share/nginx/html/admin
EXPOSE 80
