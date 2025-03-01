FROM node:16-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy the application
COPY . .

# Build for production
# RUN npm run build

# For development
CMD ["npm", "start"]