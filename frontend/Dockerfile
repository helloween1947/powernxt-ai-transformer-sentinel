FROM node:24-alpine AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_API_BASE_URL
ARG VITE_FOCUSED_ASSET_ID=powernxt-single-transformer
ARG VITE_DEFAULT_RUN_ID=single-transformer-demo-v1
ENV VITE_DATA_MODE=live VITE_API_BASE_URL=$VITE_API_BASE_URL VITE_FOCUSED_ASSET_ID=$VITE_FOCUSED_ASSET_ID VITE_DEFAULT_SOURCE=simulator VITE_DEFAULT_RUN_ID=$VITE_DEFAULT_RUN_ID
RUN npm run build
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY integration/single-transformer.nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
