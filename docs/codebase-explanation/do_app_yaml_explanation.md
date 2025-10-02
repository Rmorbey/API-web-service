# 📚 .do/app.yaml - Complete Code Explanation

## 🎯 **Overview**

This file is the **DigitalOcean App Platform configuration** that tells DigitalOcean how to deploy and run your API. It's like a **deployment blueprint** that specifies the server requirements, environment variables, and deployment settings for your application.

## 📁 **File Structure Context**

```
.do/app.yaml  ← YOU ARE HERE (DigitalOcean Configuration)
├── main.py                    (Application entry point)
├── multi_project_api.py       (FastAPI application)
├── requirements.txt           (Python dependencies)
└── .env.example              (Environment variables template)
```

## 🔍 **Line-by-Line Code Explanation**

### **1. Application Metadata (Lines 1-5)**

```yaml
name: multi-project-api
services:
  - name: api
    source_dir: /
```

**What this does:**
- **Application name**: `multi-project-api` - identifies your app in DigitalOcean
- **Service definition**: Creates a service called `api`
- **Source directory**: `/` - tells DigitalOcean to use the root directory as the source

**Why this structure?**
- **Single service**: Your API is one service (not microservices)
- **Root directory**: All code is in the root, not in subdirectories
- **Simple naming**: Clear, descriptive names for easy management

### **2. Source Configuration (Lines 6-10)**

```yaml
    github:
      repo: russellmorbey/API-web-service
      branch: main
      deploy_on_push: true
```

**What this does:**
- **GitHub integration**: Connects to your GitHub repository
- **Repository**: `russellmorbey/API-web-service` - your GitHub repo
- **Branch**: `main` - which branch to deploy from
- **Auto-deploy**: `deploy_on_push: true` - automatically deploys when you push to main

**Why these settings?**
- **GitHub integration**: Easy deployment from your code repository
- **Main branch**: Deploys from your stable main branch
- **Auto-deploy**: No manual deployment needed - just push code

### **3. Runtime Configuration (Lines 11-15)**

```yaml
    run_command: python main.py --host 0.0.0.0 --port $PORT
    environment_slug: python
    instance_count: 1
    instance_size_slug: basic-xxs
```

**What this does:**
- **Run command**: `python main.py --host 0.0.0.0 --port $PORT` - how to start your app
- **Environment**: `python` - tells DigitalOcean this is a Python app
- **Instance count**: `1` - number of server instances to run
- **Instance size**: `basic-xxs` - smallest/cheapest instance size

**Why these settings?**
- **Host 0.0.0.0**: Binds to all network interfaces (required for containers)
- **Port $PORT**: Uses DigitalOcean's assigned port
- **Single instance**: Cost-effective for low traffic
- **Basic-xxs**: Cheapest option for testing and low traffic

### **4. Network Configuration (Lines 16-20)**

```yaml
    http_port: 8000
    health_check:
      http_path: /health
      initial_delay_seconds: 30
      period_seconds: 10
      timeout_seconds: 5
      success_threshold: 1
      failure_threshold: 3
```

**What this does:**
- **HTTP port**: `8000` - port your app listens on
- **Health check**: `/health` - endpoint to check if app is healthy
- **Initial delay**: `30` seconds - wait before first health check
- **Check interval**: `10` seconds - how often to check health
- **Timeout**: `5` seconds - how long to wait for response
- **Success threshold**: `1` - how many successful checks needed
- **Failure threshold**: `3` - how many failures before marking unhealthy

**Why these settings?**
- **Health monitoring**: Ensures your app is running properly
- **Graceful startup**: Gives app time to start up
- **Failure detection**: Quickly detects when app is down
- **Reliability**: Helps maintain service availability

### **5. Environment Variables (Lines 21-50)**

```yaml
    envs:
      - key: ENVIRONMENT
        value: production
      - key: HOST
        value: "0.0.0.0"
      - key: PORT
        value: "8000"
      - key: LOG_LEVEL
        value: INFO
      - key: DEBUG
        value: "false"
      - key: CACHE_DURATION_HOURS
        value: "24"
      - key: CACHE_COMPRESSION
        value: "true"
      - key: MAX_CALLS_PER_15MIN
        value: "100"
      - key: MAX_CALLS_PER_DAY
        value: "1000"
```

**What this does:**
- **Production settings**: Sets environment to production
- **Server configuration**: Configures host and port
- **Logging**: Sets appropriate log level for production
- **Debug mode**: Disables debug mode for security
- **Cache settings**: Configures caching behavior
- **Rate limiting**: Sets API rate limits

**Why these values?**
- **Production mode**: Optimized for production use
- **Security**: Debug mode disabled
- **Performance**: Appropriate cache and rate limit settings
- **Monitoring**: INFO level logging for production

### **6. Secret Environment Variables (Lines 51-80)**

```yaml
      # These should be set as secrets in the DigitalOcean dashboard
      - key: API_KEY
        value: "your_api_key_here"
      - key: FRONTEND_ACCESS_TOKEN
        value: "your_frontend_access_token_here"
      - key: ALLOWED_ORIGINS
        value: "https://www.russellmorbey.co.uk,https://russellmorbey.co.uk"
      - key: STRAVA_CLIENT_ID
        value: "your_strava_client_id_here"
      - key: STRAVA_CLIENT_SECRET
        value: "your_strava_client_secret_here"
      - key: STRAVA_ACCESS_TOKEN
        value: "your_strava_access_token_here"
      - key: JUSTGIVING_URL
        value: "https://www.justgiving.com/fundraising/RussellMorbey-HackneyHalf"
      - key: JAWG_ACCESS_TOKEN
        value: "your_jawg_access_token_here"
```

**What this does:**
- **API security**: Sets up API keys and tokens
- **CORS configuration**: Configures allowed origins
- **External services**: Sets up Strava and JustGiving credentials
- **Map service**: Configures Jawg Maps token

**Security Notes:**
- **Secrets**: These should be set as secrets in DigitalOcean dashboard
- **No hardcoding**: Never put real secrets in this file
- **Environment separation**: Different values for different environments

### **7. Build Configuration (Lines 81-90)**

```yaml
    build_command: pip install -r requirements.txt
    build_pack: python
    build_pack_version: "3.11"
```

**What this does:**
- **Build command**: `pip install -r requirements.txt` - installs Python dependencies
- **Build pack**: `python` - tells DigitalOcean to use Python build pack
- **Python version**: `3.11` - specifies Python version to use

**Why these settings?**
- **Dependency installation**: Installs all required packages
- **Python version**: Ensures consistent Python version
- **Build process**: Automated build and deployment

### **8. Resource Configuration (Lines 91-100)**

```yaml
    resources:
      cpu: 0.25
      memory: 512
      disk: 1024
```

**What this does:**
- **CPU**: `0.25` cores - quarter of a CPU core
- **Memory**: `512` MB - half a gigabyte of RAM
- **Disk**: `1024` MB - 1 gigabyte of disk space

**Why these values?**
- **Cost effective**: Minimal resources for low traffic
- **Sufficient**: Enough for basic API operations
- **Scalable**: Can be increased as needed

### **9. Scaling Configuration (Lines 101-110)**

```yaml
    scaling:
      min_instances: 1
      max_instances: 3
      target_cpu_percent: 70
      target_memory_percent: 80
```

**What this does:**
- **Min instances**: `1` - always keep at least 1 instance running
- **Max instances**: `3` - can scale up to 3 instances
- **CPU threshold**: `70%` - scale up when CPU usage exceeds 70%
- **Memory threshold**: `80%` - scale up when memory usage exceeds 80%

**Why these settings?**
- **Always available**: At least 1 instance always running
- **Cost control**: Maximum of 3 instances to control costs
- **Performance**: Scales up when resources are needed
- **Efficiency**: Balances performance and cost

### **10. Database Configuration (Lines 111-120)**

```yaml
    databases:
      - name: api-db
        engine: POSTGRES
        version: "15"
        size: db-s-1vcpu-1gb
        num_nodes: 1
```

**What this does:**
- **Database name**: `api-db` - name of the database
- **Engine**: `POSTGRES` - uses PostgreSQL database
- **Version**: `15` - PostgreSQL version 15
- **Size**: `db-s-1vcpu-1gb` - 1 CPU, 1GB RAM database
- **Nodes**: `1` - single database node

**Why PostgreSQL?**
- **Reliability**: Robust, production-ready database
- **Performance**: Good performance for API workloads
- **Features**: Rich feature set for complex queries
- **Scalability**: Can scale as needed

## 🎯 **Key Learning Points**

### **1. DigitalOcean App Platform**
- **Platform as a Service**: Managed platform for deploying apps
- **GitHub integration**: Deploys directly from GitHub
- **Auto-scaling**: Automatically scales based on demand
- **Managed services**: Handles infrastructure management

### **2. Configuration Management**
- **Environment variables**: Secure way to manage configuration
- **Secrets management**: Secure handling of sensitive data
- **Environment separation**: Different configs for different environments
- **Version control**: Configuration in version control

### **3. Application Deployment**
- **Build process**: Automated build and deployment
- **Health monitoring**: Continuous health checks
- **Resource management**: CPU, memory, and disk allocation
- **Scaling**: Automatic scaling based on demand

### **4. Security Best Practices**
- **Secrets handling**: Secure management of API keys
- **Environment separation**: Different configs for different environments
- **Access control**: Proper CORS and authentication setup
- **Monitoring**: Health checks and logging

### **5. Cost Optimization**
- **Resource sizing**: Right-sized resources for your needs
- **Scaling limits**: Controlled scaling to manage costs
- **Instance management**: Efficient instance usage
- **Database sizing**: Appropriate database resources

## 🚀 **How This Fits Into Your Learning**

This file demonstrates:
- **Cloud deployment**: How to deploy applications to cloud platforms
- **Configuration management**: How to manage application configuration
- **Infrastructure as Code**: How to define infrastructure in code
- **Platform services**: How to use managed platform services
- **Production deployment**: How to deploy applications professionally

**Next**: We'll explore the `Dockerfile` to understand containerization! 🎉
