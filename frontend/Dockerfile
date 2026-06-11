FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

RUN chown -R node:node /app
USER node

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
