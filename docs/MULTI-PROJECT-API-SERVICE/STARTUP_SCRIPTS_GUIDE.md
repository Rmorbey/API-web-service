# 🚀 Startup Scripts Guide

## 📋 **Overview**

Separate startup scripts for development and production environments with proper environment-based access control for demo endpoints.

## 🎯 **Available Scripts**

### **1. Development Script: `start_development.sh`**
- ✅ **Environment**: `ENVIRONMENT=development`
- ✅ **Demo endpoints**: ENABLED
- ✅ **Auto-reload**: Enabled for development
- ✅ **Debug logging**: Full debug output
- ✅ **Demo pages**: Accessible

### **2. Production Script: `start_production.sh`**
- ✅ **Environment**: `ENVIRONMENT=production`
- ❌ **Demo endpoints**: DISABLED (403 Forbidden)
- ❌ **Auto-reload**: Disabled for stability
- ✅ **Info logging**: Production-level logging
- ❌ **Demo pages**: Blocked (403 Forbidden)

## 🔧 **Usage**

### **Development Mode:**
```bash
# Start in development mode (demo endpoints enabled)
./start_development.sh
```

**Output:**
```
🚀 Starting API Web Service (Development Mode)...
📦 Activating virtual environment...
🔑 Loading environment variables...
🔧 Setting development environment...
📋 Installing development dependencies...
🌐 Starting development server on http://0.0.0.0:8000
📊 API Documentation: http://0.0.0.0:8000/docs
💰 Fundraising Demo: http://0.0.0.0:8000/fundraising-demo (ENABLED)
🔧 Environment: DEVELOPMENT (Demo endpoints enabled)
```

### **Production Mode:**
```bash
# Start in production mode (demo endpoints disabled)
./start_production.sh
```

**Output:**
```
🚀 Starting API Web Service (Production Mode)...
📦 Activating virtual environment...
🔑 Loading environment variables...
🔧 Setting production environment...
📋 Installing production dependencies...
🌐 Starting production server on http://0.0.0.0:8000
📊 API Documentation: http://0.0.0.0:8000/docs
🚫 Fundraising Demo: http://0.0.0.0:8000/fundraising-demo (DISABLED)
🔧 Environment: PRODUCTION (Demo endpoints disabled)
```

## 🧪 **Testing Environment Control**

### **Test Development Mode:**
```bash
# Start development server
./start_development.sh

# In another terminal, test demo endpoints
curl http://localhost:8000/fundraising-demo
# Should return: Fundraising demo page HTML

curl http://localhost:8000/api/fundraising/demo/data
# Should return: Fundraising data JSON
```

### **Test Production Mode:**
```bash
# Start production server
./start_production.sh

# In another terminal, test demo endpoints
curl http://localhost:8000/demo
# Should return: 403 Forbidden

curl http://localhost:8000/api/fundraising/demo/data
# Should return: 403 Forbidden with error message
```

## 🔍 **Key Differences**

| Feature | Development | Production |
|---------|-------------|------------|
| **Environment** | `development` | `production` |
| **Demo Endpoints** | ✅ Enabled | ❌ Disabled (403) |
| **Demo Pages** | ✅ Accessible | ❌ Blocked (403) |
| **Auto-reload** | ✅ Enabled | ❌ Disabled |
| **Logging Level** | `debug` | `info` |
| **API Documentation** | ✅ Available | ✅ Available |
| **Protected Endpoints** | ✅ Available | ✅ Available |

## 🛡️ **Security Benefits**

### **1. Clear Environment Separation**
- **Development**: Full access to all features including demos
- **Production**: Only production endpoints accessible

### **2. Explicit Environment Setting**
- **Scripts force environment**: No reliance on `.env` file settings
- **Clear indication**: Scripts show which environment is active
- **Consistent behavior**: Same environment every time

### **3. Easy Testing**
- **Quick switching**: Easy to test both environments
- **Clear feedback**: Scripts show what's enabled/disabled
- **No confusion**: Clear indication of current mode

## 📝 **Script Features**

### **Common Features (Both Scripts):**
- ✅ **Virtual environment activation**
- ✅ **Environment variable loading**
- ✅ **Dependency installation**
- ✅ **Single worker** (prevents duplicate Strava API calls)
- ✅ **Access logging**
- ✅ **Error handling**

### **Development-Specific:**
- ✅ **Auto-reload** (`--reload` flag)
- ✅ **Debug logging** (`--log-level debug`)
- ✅ **Demo endpoints enabled**
- ✅ **Development environment forced**

### **Production-Specific:**
- ✅ **No auto-reload** (stability)
- ✅ **Info logging** (`--log-level info`)
- ✅ **Demo endpoints disabled**
- ✅ **Production environment forced**

## 🎯 **Best Practices**

### **1. Development Workflow:**
```bash
# Always use development script for local development
./start_development.sh

# Test demo endpoints work
curl http://localhost:8000/demo

# Test protected endpoints work
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/strava-integration/feed
```

### **2. Production Testing:**
```bash
# Test production mode locally before deployment
./start_production.sh

# Verify demo endpoints are blocked
curl http://localhost:8000/demo
# Should return 403 Forbidden

# Verify protected endpoints still work
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/strava-integration/feed
```

### **3. Deployment:**
```bash
# DigitalOcean automatically uses production environment
# Demo endpoints will be automatically disabled
# No additional configuration needed
```

## ✅ **Benefits**

1. **Clear Environment Control** - Explicit environment setting
2. **Easy Testing** - Quick switching between modes
3. **Security** - Demo endpoints automatically disabled in production
4. **Development Efficiency** - Auto-reload and debug logging in development
5. **Production Stability** - No auto-reload and proper logging in production
6. **Clear Feedback** - Scripts show what's enabled/disabled

## 🚀 **Quick Start**

```bash
# For development (demo endpoints enabled)
./start_development.sh

# For production testing (demo endpoints disabled)
./start_production.sh
```

**Your environment-based access control is now fully automated and easy to test!** 🎯