#!/bin/bash
# SSL/TLS Setup Script for ModPorter AI
# Day 6: Production security configuration

set -e

DOMAIN=${1:-localhost}
SSL_DIR="./ssl"

echo "🔒 Setting up SSL/TLS for domain: ${DOMAIN}"

# Create SSL directory
mkdir -p ${SSL_DIR}

# Generate Diffie-Hellman parameters
echo "🔑 Generating Diffie-Hellman parameters..."
openssl dhparam -out ${SSL_DIR}/dhparam.pem 2048

if [ "$DOMAIN" = "localhost" ]; then
    echo "🏠 Generating self-signed certificate for development..."
    
    # Generate private key
    openssl genrsa -out ${SSL_DIR}/key.pem 2048
    
    # Generate certificate signing request
    openssl req -new -key ${SSL_DIR}/key.pem -out ${SSL_DIR}/cert.csr -subj "/C=US/ST=CA/L=San Francisco/O=ModPorter AI/CN=${DOMAIN}"
    
    # Generate self-signed certificate
    openssl x509 -req -in ${SSL_DIR}/cert.csr -signkey ${SSL_DIR}/key.pem -out ${SSL_DIR}/cert.pem -days 365
    
    # Clean up CSR
    rm ${SSL_DIR}/cert.csr
    
    echo "✅ Self-signed certificate generated successfully"
else
    echo "🌐 Setting up Let's Encrypt certificate for production domain: ${DOMAIN}"
    
    # Check if certbot is installed
    if ! command -v certbot &> /dev/null; then
        echo "📦 Installing certbot..."
        sudo apt-get update
        sudo apt-get install -y certbot python3-certbot-nginx
    fi
    
    # Stop nginx if running
    sudo systemctl stop nginx 2>/dev/null || true
    
    # Generate Let's Encrypt certificate
    sudo certbot certonly --standalone \
        --preferred-challenges http \
        --email admin@${DOMAIN} \
        --agree-tos \
        --no-eff-email \
        -d ${DOMAIN}
    
    # Copy certificates to SSL directory
    sudo cp /etc/letsencrypt/live/${DOMAIN}/fullchain.pem ${SSL_DIR}/cert.pem
    sudo cp /etc/letsencrypt/live/${DOMAIN}/privkey.pem ${SSL_DIR}/key.pem
    
    # Set correct permissions
    sudo chown $(whoami):$(whoami) ${SSL_DIR}/*.pem
    chmod 600 ${SSL_DIR}/key.pem
    chmod 644 ${SSL_DIR}/cert.pem
    
    # Setup auto-renewal
    echo "🔄 Setting up auto-renewal..."
    (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet --post-hook 'docker-compose -f ${PWD}/docker-compose.prod.yml restart frontend'") | crontab -
    
    echo "✅ Let's Encrypt certificate configured successfully"
fi

# Update nginx configuration for SSL
echo "📝 Creating SSL-enabled nginx configuration..."
cat > ./frontend/nginx-ssl.conf << EOF
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    # Logging
    log_format main '\$remote_addr - \$remote_user [\$time_local] "\$request" '
                    '\$status \$body_bytes_sent "\$http_referer" '
                    '"\$http_user_agent" "\$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log warn;

    # Performance
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;

    # Rate limiting
    limit_req_zone \$binary_remote_addr zone=api:10m rate=10r/m;
    limit_req_zone \$binary_remote_addr zone=upload:10m rate=5r/m;

    # HTTP to HTTPS redirect
    server {
        listen 80;
        server_name ${DOMAIN};
        return 301 https://\$server_name\$request_uri;
    }

    # HTTPS server
    server {
        listen 443 ssl http2;
        server_name ${DOMAIN};
        root /usr/share/nginx/html;
        index index.html;

        # SSL Configuration
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_dhparam /etc/nginx/ssl/dhparam.pem;

        # SSL Security Settings
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
        ssl_ecdh_curve secp384r1;
        ssl_session_timeout 10m;
        ssl_session_cache shared:SSL:10m;
        ssl_session_tickets off;
        ssl_stapling on;
        ssl_stapling_verify on;

        # Security headers
        add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
        add_header X-Frame-Options "DENY" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "no-referrer-when-downgrade" always;
        add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self' https://${DOMAIN}:8080 wss://${DOMAIN}:8080; frame-ancestors 'none';" always;

        # API proxy to backend with rate limiting
        location /api/v1/upload {
            limit_req zone=upload burst=5 nodelay;
            proxy_pass http://backend:8000/api/v1/upload;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
            
            # Increase upload size limit
            client_max_body_size 100M;
            proxy_request_buffering off;
            
            # Extended timeouts for uploads
            proxy_connect_timeout 300s;
            proxy_send_timeout 300s;
            proxy_read_timeout 300s;
        }

        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://backend:8000/api/;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
            
            # WebSocket support for real-time features
            proxy_http_version 1.1;
            proxy_set_header Upgrade \$http_upgrade;
            proxy_set_header Connection "upgrade";
            
            # Timeouts
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # Handle client-side routing
        location / {
            try_files \$uri \$uri/ /index.html;
        }

        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
            add_header Vary Accept-Encoding;
        }

        # Health check endpoint
        location /health {
            access_log off;
            add_header Content-Type text/plain;
            return 200 "healthy\n";
        }

        # Nginx status for monitoring
        location /nginx_status {
            stub_status on;
            access_log off;
            allow 172.20.0.0/16;
            deny all;
        }
    }
}
EOF

echo "🔒 SSL/TLS setup completed successfully!"
echo ""
echo "📋 SSL Configuration Summary:"
echo "  🔑 Private key: ${SSL_DIR}/key.pem"
echo "  📜 Certificate: ${SSL_DIR}/cert.pem"
echo "  🔐 DH parameters: ${SSL_DIR}/dhparam.pem"
echo "  📝 Nginx config: ./frontend/nginx-ssl.conf"
echo ""
echo "🚀 To use SSL in production:"
echo "  1. Copy nginx-ssl.conf to nginx.conf in your frontend directory"
echo "  2. Update docker-compose.prod.yml to use the SSL configuration"
echo "  3. Ensure your domain DNS points to your server"
echo "  4. Deploy with: ./scripts/deploy.sh production"