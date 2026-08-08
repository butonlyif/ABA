FROM node:22-alpine AS build
WORKDIR /app
COPY projects/aba/frontend/package.json projects/aba/frontend/package-lock.json* ./
RUN npm install
COPY projects/aba/frontend/ .
RUN npm run build

FROM nginx:1.27-alpine
COPY projects/aba/frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
