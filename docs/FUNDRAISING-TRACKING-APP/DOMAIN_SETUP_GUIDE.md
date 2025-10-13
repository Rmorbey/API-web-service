# 🌐 Domain Setup Guide: www.russellmorbey.co.uk

## 🎯 **Your Domain Structure**

```
www.russellmorbey.co.uk/
├── / (existing portfolio)
├── /fundraising-app (React frontend)
└── /api (FastAPI backend)
```

## 🚀 **Setup Options**

### **Option 1: DigitalOcean App Platform + Custom Domain (Recommended)**

#### **Step 1: Deploy API to DigitalOcean**
1. Deploy your API to DigitalOcean App Platform
2. Get default URL: `https://your-app-name.ondigitalocean.app`

#### **Step 2: Configure Custom Domain**
1. In DigitalOcean App Platform:
   - Go to **Settings** → **Domains**
   - Add custom domain: `api.russellmorbey.co.uk`
   - DigitalOcean will provide DNS records to add

#### **Step 3: Configure DNS Records**
Add these DNS records to your domain provider:

```
Type: CNAME
Name: api
Value: your-app-name.ondigitalocean.app
TTL: 3600
```

#### **Step 4: Configure Main Domain Routing**
Set up routing on your main domain to proxy `/api/*` requests:

**If using Cloudflare:**
```javascript
// Cloudflare Workers script
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const url = new URL(request.url)
  
  if (url.pathname.startsWith('/api/')) {
    // Proxy to your API
    const apiUrl = `https://api.russellmorbey.co.uk${url.pathname}${url.search}`
    return fetch(apiUrl, {
      method: request.method,
      headers: request.headers,
      body: request.body
    })
  }
  
  // Serve your main site
  return fetch(request)
}
```

**If using nginx:**
```nginx
server {
    listen 80;
    server_name www.russellmorbey.co.uk;
    
    # Proxy API requests
    location /api/ {
        proxy_pass https://api.russellmorbey.co.uk/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Serve your main site
    location / {
        root /var/www/html;
        index index.html;
    }
}
```

### **Option 2: All on One Server (Simpler)**

#### **Step 1: Deploy to VPS**
1. Create a DigitalOcean Droplet (VPS)
2. Install nginx, Node.js, and Python
3. Deploy both frontend and backend

#### **Step 2: Configure nginx**
```nginx
server {
    listen 80;
    server_name www.russellmorbey.co.uk;
    
    # Serve React app at /fundraising-app
    location /fundraising-app {
        alias /var/www/fundraising-app/build;
        try_files $uri $uri/ /fundraising-app/index.html;
    }
    
    # Proxy API requests
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Serve your main portfolio
    location / {
        root /var/www/portfolio;
        index index.html;
    }
}
```

## 🔧 **Frontend Configuration Updates**

### **Update API Base URL**
In your React app, update the API base URL:

```javascript
// config.js
const API_BASE_URL = process.env.NODE_ENV === 'production' 
  ? 'https://www.russellmorbey.co.uk/api'
  : 'http://localhost:8000';

export default API_BASE_URL;
```

### **Update API Calls**
```javascript
// In your React components
import API_BASE_URL from './config';

const fetchActivities = async () => {
  const response = await fetch(`${API_BASE_URL}/strava-integration/feed`, {
    headers: {
      'X-API-Key': 'your_api_key_here'
    }
  });
  return response.json();
};
```

## 🔒 **Security Considerations**

### **CORS Configuration**
Update your FastAPI CORS settings:

```python
# In multi_project_api.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://www.russellmorbey.co.uk",
        "https://russellmorbey.co.uk",
        "http://localhost:3000",  # For development
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

### **API Key Security**
- Keep your API keys secure
- Use environment variables
- Consider rate limiting

## 📋 **Deployment Checklist**

### **API Deployment:**
- [ ] Deploy to DigitalOcean App Platform
- [ ] Configure custom domain `api.russellmorbey.co.uk`
- [ ] Set all environment variables as secrets
- [ ] Test API endpoints

### **Frontend Deployment:**
- [ ] Build React app for production
- [ ] Update API base URL to `https://www.russellmorbey.co.uk/api`
- [ ] Deploy to your hosting provider
- [ ] Configure routing for `/fundraising-app`

### **Domain Configuration:**
- [ ] Add DNS records for `api.russellmorbey.co.uk`
- [ ] Configure reverse proxy for `/api/*` routing
- [ ] Test all endpoints

## 🎯 **Final URLs**

After setup, your URLs will be:

- **Portfolio**: `https://www.russellmorbey.co.uk/`
- **Fundraising App**: `https://www.russellmorbey.co.uk/fundraising-app`
- **API Health**: `https://www.russellmorbey.co.uk/api/strava-integration/health`
- **API Feed**: `https://www.russellmorbey.co.uk/api/strava-integration/feed`

## 💰 **Cost Breakdown**

### **Option 1 (DigitalOcean App Platform):**
- API hosting: $5/month
- Domain: Already owned
- **Total**: $5/month

### **Option 2 (VPS):**
- VPS hosting: $6-12/month
- Domain: Already owned
- **Total**: $6-12/month

## 🚀 **Recommended Next Steps**

1. **Start with Option 1** (DigitalOcean App Platform)
2. **Deploy your API first**
3. **Test the API endpoints**
4. **Then configure your frontend**
5. **Finally set up domain routing**

This approach gives you a professional, scalable setup with your existing domain! 🎉
