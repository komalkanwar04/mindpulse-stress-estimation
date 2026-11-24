# Multi-stage Dockerfile for React/Vite Frontend
FROM node:18-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# Pass build-time environment variables for API endpoints
ARG VITE_BACKEND_URL
ARG VITE_ML_SERVICE_URL
ENV VITE_BACKEND_URL=$VITE_BACKEND_URL
ENV VITE_ML_SERVICE_URL=$VITE_ML_SERVICE_URL

RUN npm run build

# Stage 2: Serve with Nginx Alpine
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
