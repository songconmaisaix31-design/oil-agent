# syntax=docker/dockerfile:1
ARG NODE_IMAGE=node:24-alpine@sha256:50c8e8ca1d27439048670df5883f32d57cf81cff6233222c893fd0d9884cbd81
FROM ${NODE_IMAGE} AS frontend
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --ignore-scripts
COPY web ./
COPY src/oil_agent/contracts/openapi.json /src/oil_agent/contracts/openapi.json
RUN npm run build

FROM nginx:1.28-alpine@sha256:a8b39bd9cf0f83869a2162827a0caf6137ddf759d50a171451b335cecc87d236 AS gateway
COPY deploy/nginx.conf /etc/nginx/nginx.conf
COPY --from=frontend /web/dist /usr/share/nginx/html
USER 101:101
EXPOSE 8080
ENTRYPOINT ["nginx"]
CMD ["-g", "daemon off;"]
