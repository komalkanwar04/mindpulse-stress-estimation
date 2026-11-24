FROM node:18-slim

WORKDIR /app

# Install build dependencies for better-sqlite3 native compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY package*.json ./
RUN npm install --production

COPY . .

# Ensure data directory exists for SQLite
RUN mkdir -p /app/data

ENV PORT=4000 \
    NODE_ENV=production \
    ML_SERVICE_URL=http://ml-service:5001

EXPOSE 4000

CMD ["npm", "start"]
