# Multi-stage build for PIR Server - Modified to skip Privacy Pass authentication
FROM swift:6.1 AS builder

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Clone homomorphic encryption library
RUN git clone https://github.com/apple/swift-homomorphic-encryption
WORKDIR /app/swift-homomorphic-encryption
RUN git checkout 1.0.3
RUN swift package experimental-install -c release --product PIRProcessDatabase

# Build the PIR Service
WORKDIR /app
COPY Package.swift Package.resolved ./
RUN swift package resolve

COPY Sources ./Sources
RUN swift package experimental-install -c release --product PIRService

# Build the database
WORKDIR /app
RUN mkdir data
COPY data/ data/
RUN cd data && ~/.swiftpm/bin/PIRProcessDatabase url-config.json

# Production image
FROM swift:6.1-slim

WORKDIR /app

# Install git for potential runtime needs
RUN apt-get update && apt-get install -y git ca-certificates && rm -rf /var/lib/apt/lists/*

# Copy the binary and database
COPY --from=builder /root/.swiftpm/bin/PIRService /usr/local/bin/PIRService
COPY --from=builder /app/data/url-*.bin /app/
COPY --from=builder /app/data/url-*.params.txtpb /app/
COPY service-config.json /app/

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/ || exit 1

# Run the server
CMD ["PIRService", "--hostname", "0.0.0.0", "--port", "8080", "service-config.json"]