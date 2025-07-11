FROM node:22-slim

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

RUN npm ci

COPY . .

# Expose port
EXPOSE 3000

# Start the application
CMD ["npm", "run", "dev"] 