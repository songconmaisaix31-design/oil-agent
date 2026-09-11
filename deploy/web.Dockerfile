# syntax=docker/dockerfile:1
ARG NODE_IMAGE=node:24-alpine
FROM ${NODE_IMAGE} AS frontend
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --ignore-scripts
COPY web ./
RUN npm run build

FROM nginx:1.28-alpine AS gateway
COPY deploy/nginx.conf /etc/nginx/nginx.conf
COPY --from=frontend /web/dist /usr/share/nginx/html
USER 101:101
EXPOSE 8080
ENTRYPOINT ["nginx"]
CMD ["-g", "daemon off;"]
