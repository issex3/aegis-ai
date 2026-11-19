FROM node:22-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ENV API_INTERNAL_URL=http://backend:8000
RUN npm run build
USER node
EXPOSE 3000
CMD ["npm", "start"]
