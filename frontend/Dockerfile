# RIFT Frontend Dockerfile (Development)
FROM node:20-slim

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# Expose Vite port
EXPOSE 5173

# Start dev server, binding to 0.0.0.0
CMD ["npm", "run", "dev", "--", "--host"]
