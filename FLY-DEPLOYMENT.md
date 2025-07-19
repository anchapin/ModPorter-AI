# 🚀 Deploy ModPorter AI to Fly.io

**Perfect choice!** Fly.io is ideal for ModPorter AI. Here's your complete deployment guide:

## 🔥 Why Fly.io is Perfect

- **🌍 Global Edge**: Deploy close to users worldwide
- **💰 Cost-Effective**: Start ~$5-15/month, scale as needed  
- **🐳 Docker-Native**: Your containers deploy seamlessly
- **⚡ Zero Cold Starts**: Always-on performance
- **🔒 Built-in SSL**: Automatic HTTPS for modporter.ai
- **📊 AI-Optimized**: Great for compute-heavy AI workloads

## 📋 Prerequisites

1. **Install Fly CLI:**
   ```bash
   # macOS/Linux
   curl -L https://fly.io/install.sh | sh
   
   # Or via package managers
   brew install flyctl  # macOS
   ```

2. **Sign up and authenticate:**
   ```bash
   flyctl auth signup  # or flyctl auth login
   ```

3. **Add payment method** (required, but free tier available)

## 🚀 Deployment Steps

### 1. **Initialize Fly App**
```bash
cd ModPorter-AI

# Create app (replace with your preferred name)
flyctl apps create modporter-ai

# Set up domains  
flyctl domains create modporter.ai
flyctl domains add www.modporter.ai
```

### 2. **Configure Secrets**
```bash
# Set your API keys and secrets
flyctl secrets set \
  OPENAI_API_KEY=your-openai-key \
  ANTHROPIC_API_KEY=your-anthropic-key \
  SECRET_KEY=your-super-secret-key-here \
  JWT_SECRET_KEY=your-jwt-secret-key \
  DB_PASSWORD=secure-database-password \
  GRAFANA_ADMIN_PASSWORD=secure-grafana-password
```

### 3. **Set Up Database** (Choose One)

#### Option A: Fly PostgreSQL (Recommended)
```bash
# Create managed PostgreSQL
flyctl postgres create --name modporter-db
flyctl postgres attach modporter-db

# Create Redis
flyctl redis create --name modporter-redis
flyctl redis attach modporter-redis
```

#### Option B: External Database
```bash
# Use external providers like Supabase, Railway, etc.
flyctl secrets set DATABASE_URL=postgresql://user:pass@host:port/db
flyctl secrets set REDIS_URL=redis://host:port
```

### 4. **Create Storage Volume**
```bash
# For persistent file storage
flyctl volumes create modporter_data --size 10
```

### 5. **Deploy!**
```bash
# Deploy using Fly.io configuration
flyctl deploy -c deploy-fly.toml

# Or deploy with custom dockerfile
flyctl deploy --dockerfile Dockerfile.fly
```

### 6. **Configure DNS**
```bash
# Get your Fly.io app IP
flyctl ips list

# In your domain registrar, set:
# A record: modporter.ai -> [your-fly-ip]
# CNAME: www.modporter.ai -> modporter.ai
```

### 7. **SSL Certificate**
```bash
# Fly.io handles SSL automatically once DNS is configured
flyctl certs create modporter.ai
flyctl certs create www.modporter.ai

# Check certificate status
flyctl certs check modporter.ai
```

## ✅ Verification

### Check Deployment
```bash
# View app status
flyctl status

# Check logs
flyctl logs

# Open in browser
flyctl open
```

### Test Endpoints
- **Frontend**: https://modporter.ai
- **API Health**: https://modporter.ai/api/v1/health
- **Upload Test**: Try uploading a mod file

## 📊 Monitoring & Scaling

### View Metrics
```bash
# App metrics
flyctl metrics

# Machine status
flyctl machine list

# Scale up/down
flyctl scale count 2  # Run 2 instances
flyctl scale memory 4096  # 4GB RAM
```

### Logs & Debugging
```bash
# Real-time logs
flyctl logs -f

# SSH into machine
flyctl ssh console

# Run commands
flyctl ssh console -C "curl localhost:8000/api/v1/health"
```

## 💰 Cost Estimation

### **Starter Setup (~$15-25/month):**
- **App**: 1 shared-cpu-1x, 512MB RAM (~$5-10/month)
- **PostgreSQL**: shared-cpu-1x, 1GB RAM (~$5-10/month)  
- **Redis**: shared-cpu-1x, 256MB RAM (~$5/month)
- **Volume**: 10GB storage (~$2/month)

### **Production Setup (~$50-100/month):**
- **App**: 2x shared-cpu-2x, 2GB RAM (~$30-50/month)
- **PostgreSQL**: dedicated-cpu-1x, 2GB RAM (~$15-25/month)
- **Redis**: shared-cpu-1x, 512MB RAM (~$8/month)
- **Volume**: 25GB storage (~$5/month)

## 🔧 Advanced Configuration

### Environment Variables
```bash
# Set additional config
flyctl secrets set \
  MAX_CONCURRENT_CONVERSIONS=10 \
  RATE_LIMIT_PER_MINUTE=20 \
  LOG_LEVEL=INFO
```

### Auto-scaling
```toml
# In deploy-fly.toml
[scaling]
  min_machines_running = 1
  max_machines_running = 10
```

### Multiple Regions
```bash
# Add regions for global deployment
flyctl regions add lhr  # London
flyctl regions add nrt  # Tokyo
flyctl regions add syd  # Sydney
```

## 🎯 Go Live Checklist

- [ ] **Fly.io app created and configured**
- [ ] **Secrets and API keys set**
- [ ] **Database and Redis attached**
- [ ] **Storage volume created**
- [ ] **DNS configured and propagated**
- [ ] **SSL certificates active**
- [ ] **Application deployed successfully**
- [ ] **Health checks passing**
- [ ] **First mod conversion tested**
- [ ] **Monitoring setup verified**

## 🚨 Troubleshooting

### Common Issues

**App won't start:**
```bash
flyctl logs  # Check error logs
flyctl ssh console  # Debug directly
```

**Database connection issues:**
```bash
flyctl postgres connect  # Test DB connection
flyctl secrets list  # Verify DATABASE_URL
```

**SSL certificate issues:**
```bash
flyctl certs check modporter.ai  # Check cert status
```

**Domain not working:**
```bash
dig modporter.ai  # Verify DNS propagation
flyctl ips list  # Confirm correct IP
```

## 🎉 You're Live!

Once deployed on Fly.io:

1. **Test thoroughly** - Upload mods, check conversions
2. **Monitor performance** - Use `flyctl metrics`  
3. **Scale as needed** - Add regions and resources
4. **Celebrate!** - You're running on world-class infrastructure! 🍾

**Your AI-powered mod conversion platform is now live globally!** 🌍

---

**Need help?** Fly.io has excellent docs and community support. Your platform is built to scale from day one!