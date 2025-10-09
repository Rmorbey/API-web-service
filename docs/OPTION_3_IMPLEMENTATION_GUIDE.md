# 🚀 Option 3: Hybrid Approach - Implementation Guide

## 🎯 **What We're Building**

**Simple Structure:**
```
App 1: russellmorbey-portfolio (Your existing portfolio + fundraising frontend)
App 2: russellmorbey-api (Your API backend - this repository)
Cloudflare Worker: Routes traffic between them
```

**Domain Structure:**
- `www.russellmorbey.co.uk/` → Portfolio App
- `www.russellmorbey.co.uk/fundraising-tracking-app` → Portfolio App  
- `www.russellmorbey.co.uk/api` → API App

## 📋 **Exact Steps You Need to Do**

### **Step 1: Deploy Your API (30 minutes)**

#### **1.1: Create DigitalOcean App for API**
1. Go to [DigitalOcean App Platform](https://cloud.digitalocean.com/apps)
2. Click **"Create App"**
3. Connect GitHub repository: `russellmorbey/API-web-service`
4. DigitalOcean will auto-detect `.do/app.yaml`

#### **1.2: Set Environment Variables as Secrets**
In DigitalOcean dashboard, add these as **SECRET** type:
```
STRAVA_API_KEY = [your actual API key]
FUNDRAISING_API_KEY = [your actual API key]  
JAWG_ACCESS_TOKEN = [your actual Jawg token]
JUSTGIVING_URL = https://www.justgiving.com/fundraising/RussellMorbey-HackneyHalf?utm_medium=FR&utm_source=CL&utm_campaign=015
STRAVA_CLIENT_ID = [your actual client ID]
STRAVA_CLIENT_SECRET = [your actual client secret]
STRAVA_ACCESS_TOKEN = [your actual access token]
STRAVA_REFRESH_TOKEN = [your actual refresh token]
STRAVA_EXPIRES_AT = [your actual expires at]
STRAVA_EXPIRES_IN = [your actual expires in]
ENVIRONMENT = production
PORT = 8080
```

#### **1.3: Deploy and Test**
1. Click **"Create Resources"**
2. Wait for deployment (5-10 minutes)
3. Test: `https://russellmorbey-api.ondigitalocean.app/api/strava-integration/health`

### **Step 2: Set Up Cloudflare (20 minutes)**

#### **2.1: Add Domain to Cloudflare**
1. Go to [Cloudflare](https://cloudflare.com) (free account)
2. Add domain: `russellmorbey.co.uk`
3. Get nameservers from Cloudflare

#### **2.2: Update DNS in GoDaddy**
1. Go to GoDaddy DNS management
2. Update nameservers to Cloudflare nameservers
3. Wait 5-15 minutes for DNS propagation

#### **2.3: Create Cloudflare Worker**
1. Go to **Workers & Pages** in Cloudflare
2. Create new Worker
3. Add this code:

```javascript
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const url = new URL(request.url)
  
  // Route API requests to your API app
  if (url.pathname.startsWith('/api/')) {
    const apiUrl = `https://russellmorbey-api.ondigitalocean.app${url.pathname}${url.search}`
    return fetch(apiUrl, {
      method: request.method,
      headers: request.headers,
      body: request.body
    })
  }
  
  // Route everything else to your portfolio app
  const portfolioUrl = `https://russellmorbey-portfolio.ondigitalocean.app${url.pathname}${url.search}`
  return fetch(portfolioUrl, {
    method: request.method,
    headers: request.headers,
    body: request.body
  })
}
```

4. Deploy Worker

### **Step 3: Update Your Portfolio App (30 minutes)**

#### **3.1: Add Fundraising Frontend to Portfolio App**
1. Access your portfolio app's repository
2. Add fundraising React app as a new service
3. Update `.do/app.yaml` to include fundraising service:

```yaml
services:
- name: portfolio
  source_dir: ./portfolio
  run_command: npm start
  environment_slug: node-js

- name: fundraising  
  source_dir: ./fundraising
  run_command: npm start
  environment_slug: node-js

routes:
- path: /
  service: portfolio
- path: /fundraising-tracking-app
  service: fundraising
```

#### **3.2: Deploy Updated Portfolio App**
1. Commit changes to portfolio repository
2. Deploy to DigitalOcean App Platform
3. Test: `https://www.russellmorbey.co.uk/fundraising-tracking-app`

### **Step 4: Test Everything (10 minutes)**

**Test Checklist:**
- [ ] `www.russellmorbey.co.uk/` → Portfolio works
- [ ] `www.russellmorbey.co.uk/api/health` → API works  
- [ ] `www.russellmorbey.co.uk/fundraising-tracking-app` → Fundraising works
- [ ] All routing works correctly

## ⏱️ **Total Time: ~90 minutes**

## 💰 **Cost Breakdown**
- **DigitalOcean API App**: $5/month
- **DigitalOcean Portfolio App**: $5/month (if not already running)
- **Cloudflare**: Free
- **Total**: $10/month

## 🎯 **What You Get**
- ✅ **Professional domain structure**
- ✅ **Separate API and frontend apps**
- ✅ **Cloudflare routing and CDN**
- ✅ **Production-optimized deployment**
- ✅ **Scalable architecture**

## 🚨 **Important Notes**
1. **Start with Step 1** - Deploy API first and test it
2. **Don't rush** - Test each step before moving to the next
3. **Keep backups** - Your current setup will keep working during changes
4. **DNS changes** - Your site might be down for 5-15 minutes during DNS propagation

## 🆘 **If Something Goes Wrong**
1. **API issues**: Check environment variables in DigitalOcean
2. **Routing issues**: Check Cloudflare Worker code
3. **DNS issues**: Wait for propagation or revert nameservers
4. **Portfolio issues**: Revert to previous version

## 🎉 **Result**
You'll have a professional, scalable setup with:
- Clean domain structure
- Separate API and frontend
- Cloudflare performance benefits
- Production-ready deployment