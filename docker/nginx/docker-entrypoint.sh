#!/bin/bash
# Production NGINX Docker Entrypoint
# Sets up dynamic upstream configuration and health checks

set -e

# Function to add/remove backend servers dynamically
update_upstream_servers() {
    local service_name=$1
    local upstream_name=$2
    local default_port=$3
    
    echo "Updating upstream servers for $service_name..."
    
    # Get container IPs for the service
    containers=$(getent hosts "$service_name" | awk '{print $1}')
    
    if [ -z "$containers" ]; then
        echo "No containers found for service: $service_name"
        return
    fi
    
    # Generate upstream configuration
    upstream_config="upstream ${upstream_name}_servers {\n"
    upstream_config+="    least_conn;\n"
    
    for ip in $containers; do
        echo "Adding server $ip:$default_port to upstream $upstream_name"
        upstream_config+="    server $ip:$default_port max_fails=3 fail_timeout=30s;\n"
    done
    
    upstream_config+="    keepalive 32;\n"
    upstream_config+="}\n\n"
    
    # Update nginx configuration
    sed -i "/upstream ${upstream_name}_servers {/,/^}/c\\$upstream_config" /etc/nginx/nginx.conf
}

# Function to check backend health
check_backend_health() {
    local service_name=$1
    local port=$2
    
    echo "Checking health of $service_name:$port..."
    
    containers=$(getent hosts "$service_name" | awk '{print $1}')
    
    for ip in $containers; do
        if curl -f -s "http://$ip:$port/api/v1/health" > /dev/null; then
            echo "✓ $service_name at $ip:$port is healthy"
            return 0
        else
            echo "✗ $service_name at $ip:$port is unhealthy"
        fi
    done
    
    return 1
}

# Function to wait for services to be ready
wait_for_services() {
    echo "Waiting for services to be ready..."
    
    # Wait for backend
    echo "Checking backend service..."
    while ! check_backend_health "backend" "8000"; do
        echo "Backend not ready, waiting..."
        sleep 5
    done
    
    # Wait for frontend
    echo "Checking frontend service..."
    while ! curl -f -s "http://frontend/api/v1/health" > /dev/null; do
        echo "Frontend not ready, waiting..."
        sleep 5
    done
    
    # Wait for AI engine
    echo "Checking AI engine service..."
    while ! curl -f -s "http://ai-engine/api/v1/health" > /dev/null; do
        echo "AI engine not ready, waiting..."
        sleep 5
    done
    
    echo "All services are ready!"
}

# Function to generate SSL certificates (for development)
generate_ssl_certs() {
    if [ ! -f "/etc/nginx/ssl/nginx-selfsigned.crt" ]; then
        echo "Generating self-signed SSL certificates..."
        mkdir -p /etc/nginx/ssl
        
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout /etc/nginx/ssl/nginx-selfsigned.key \
            -out /etc/nginx/ssl/nginx-selfsigned.crt \
            -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
        
        echo "SSL certificates generated."
    fi
}

# Function to setup monitoring endpoints
setup_monitoring() {
    echo "Setting up monitoring configuration..."
    
    # Create monitoring configuration
    cat > /etc/nginx/conf.d/monitoring.conf << 'EOF'
# Monitoring and metrics configuration

# Health check endpoint
location /health {
    access_log off;
    return 200 "healthy\n";
    add_header Content-Type text/plain;
}

# Ready check endpoint
location /ready {
    access_log off;
    # Check if backend services are ready
    content_by_lua_block {
        local http = require "resty.http"
        local httpc = http.new()
        
        local res, err = httpc:request_uri("http://backend:8000/api/v1/health", {
            method = "GET",
            timeout = 5000
        })
        
        if not res or res.status ~= 200 then
            ngx.status = 503
            ngx.say("Service Unavailable")
            ngx.exit(503)
        end
        
        ngx.say("Ready")
    }
}

# Metrics endpoint for Prometheus
location /nginx_metrics {
    access_log off;
    
    # Export NGINX metrics
    content_by_lua_block {
        local ngx_req_status = require "ngx.req_status"
        ngx_req_status.init_worker()
        
        local metrics = {
            ["nginx_http_requests_total"] = ngx.var.requests,
            ["nginx_connections_active"] = ngx.var.connections_active,
            ["nginx_connections_reading"] = ngx.var.connections_reading,
            ["nginx_connections_writing"] = ngx.var.connections_writing,
            ["nginx_connections_waiting"] = ngx.var.connections_waiting
        }
        
        for name, value in pairs(metrics) do
            ngx.say(name .. " " .. value)
        end
    }
}
EOF
}

# Function to optimize NGINX for production
optimize_nginx() {
    echo "Optimizing NGINX for production..."
    
    # Set worker processes
    sed -i "s/worker_processes.*;/worker_processes auto;/" /etc/nginx/nginx.conf
    
    # Set worker connections
    sed -i "s/worker_connections.*;/worker_connections 8192;/" /etc/nginx/nginx.conf
    
    # Create performance configuration
    cat > /etc/nginx/conf.d/performance.conf << 'EOF'
# Performance optimization

# Worker processes and connections
worker_processes auto;
worker_rlimit_nofile 65535;

# Events configuration
events {
    worker_connections 8192;
    use epoll;
    multi_accept on;
}

# HTTP configuration
http {
    # Basic settings
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    server_tokens off;
    
    # MIME types
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    
    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for" '
                    'rt=$request_time uct="$upstream_connect_time" '
                    'uht="$upstream_header_time" urt="$upstream_response_time"';
    
    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log warn;
    
    # Performance settings
    client_max_body_size 100M;
    client_body_buffer_size 128k;
    client_header_buffer_size 1k;
    large_client_header_buffers 4 4k;
    client_body_timeout 60;
    client_header_timeout 60;
    send_timeout 60;
    
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
    
    # Brotli compression (if module available)
    # brotli on;
    # brotli_comp_level 6;
    # brotli_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    
    # Open file cache
    open_file_cache max=10000 inactive=20s;
    open_file_cache_valid 30s;
    open_file_cache_min_uses 2;
    open_file_cache_errors on;
    
    # Connection limits
    reset_timedout_connection on;
    client_body_buffer_size 128k;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=upload_limit:10m rate=2r/s;
    limit_conn_zone $binary_remote_addr zone=conn_limit_per_ip:10m;
}
EOF
}

# Main execution
echo "Starting NGINX initialization..."

# Create log directory
mkdir -p /var/log/nginx

# Generate htpasswd file for admin access (change password in production)
echo "admin:$(openssl passwd -apr1 'changeme')" > /etc/nginx/.htpasswd

# Wait for services to be ready
wait_for_services

# Update upstream servers dynamically
update_upstream_servers "backend" "backend" "8000"
update_upstream_servers "ai-engine" "ai_engine" "8001"
update_upstream_servers "frontend" "frontend" "80"

# Setup monitoring
setup_monitoring

# Optimize NGINX
optimize_nginx

# Generate SSL certificates for development (comment out in production)
# generate_ssl_certs

# Test NGINX configuration
echo "Testing NGINX configuration..."
nginx -t

if [ $? -eq 0 ]; then
    echo "NGINX configuration test passed."
else
    echo "NGINX configuration test failed!"
    exit 1
fi

# Start NGINX
echo "Starting NGINX..."
exec nginx -g "daemon off;"
