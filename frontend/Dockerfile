# build env
FROM node:21.7.1-alpine
WORKDIR /app
COPY package.json package.json
COPY package-lock.json package-lock.json
RUN npm install
COPY . ./
RUN npm run build
CMD ["npx", "-y", "http-server", "-p", "8000", "/app/result_build"]
 
