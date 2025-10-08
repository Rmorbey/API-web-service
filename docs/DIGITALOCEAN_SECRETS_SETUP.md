# 🔐 DigitalOcean App Platform Secrets Setup Guide

## 📋 **Your Environment Variables**

Based on your `.env` file, here are all the secrets you need to set in DigitalOcean:

### **API Security Keys:**
- `STRAVA_API_KEY` = `your_strava_api_key_here`
- `FUNDRAISING_API_KEY` = `your_fundraising_api_key_here`

### **Frontend Access Control:**
- `FRONTEND_ACCESS_TOKEN` = `your_frontend_access_token_here`
- `ALLOWED_ORIGINS` = `http://localhost:3000,http://localhost:5173,http://localhost:8000,https://www.russellmorbey.co.uk,https://russellmorbey.co.uk`

### **JustGiving Configuration:**
- `JUSTGIVING_URL` = `https://www.justgiving.com/fundraising/RussellMorbey-HackneyHalf?utm_medium=FR&utm_source=CL&utm_campaign=015`

### **Jawg Maps Configuration:**
- `JAWG_ACCESS_TOKEN` = `your_jawg_access_token_here`

### **Strava API Configuration:**
- `STRAVA_CLIENT_ID` = `your_strava_client_id_here`
- `STRAVA_CLIENT_SECRET` = `your_strava_client_secret_here`

### **Strava Tokens:**
- `STRAVA_ACCESS_TOKEN` = `your_strava_access_token_here`
- `STRAVA_REFRESH_TOKEN` = `your_strava_refresh_token_here`
- `STRAVA_EXPIRES_AT` = `your_strava_expires_at_here`
- `STRAVA_EXPIRES_IN` = `your_strava_expires_in_here`

### **Environment Configuration:**
- `ENVIRONMENT` = `production`
- `PORT` = `8080`

### **Automated Token Refresh (Optional):**
- `DIGITALOCEAN_API_TOKEN` = `your_digitalocean_api_token_here`
- `DIGITALOCEAN_APP_ID` = `your_digitalocean_app_id_here`

## 🚀 **Step-by-Step Setup in DigitalOcean**

### **1. Deploy Your App:**
```bash
# Push your code to GitHub
git add .
git commit -m "Add production deployment configuration"
git push origin main
```

### **2. Create App in DigitalOcean:**
1. Go to [DigitalOcean App Platform](https://cloud.digitalocean.com/apps)
2. Click **"Create App"**
3. Connect your GitHub repository: `russellmorbey/API-web-service`
4. DigitalOcean will detect `.do/app.yaml` automatically

### **3. Set Environment Variables as Secrets:**

#### **Go to App Settings:**
1. Click on your app in DigitalOcean
2. Go to **Settings** → **App-Level Environment Variables**
3. Click **"Edit"**

#### **Add Each Secret:**

**Add STRAVA_API_KEY:**
- **Name**: `STRAVA_API_KEY`
- **Value**: `your_strava_api_key_here`
- **Type**: `SECRET` (not plain text)
- **Scope**: `RUN_TIME`

**Add FUNDRAISING_API_KEY:**
- **Name**: `FUNDRAISING_API_KEY`
- **Value**: `your_fundraising_api_key_here`
- **Type**: `SECRET`
- **Scope**: `RUN_TIME`

**Add FRONTEND_ACCESS_TOKEN:**
- **Name**: `FRONTEND_ACCESS_TOKEN`
- **Value**: `your_frontend_access_token_here`
- **Type**: `SECRET`
- **Scope**: `RUN_TIME`

**Add ALLOWED_ORIGINS:**
- **Name**: `ALLOWED_ORIGINS`
- **Value**: `http://localhost:3000,http://localhost:5173,http://localhost:8000,https://www.russellmorbey.co.uk,https://russellmorbey.co.uk`
- **Type**: `SECRET`
- **Scope**: `RUN_TIME`

**Add JUSTGIVING_URL:**
- **Name**: `JUSTGIVING_URL`
- **Value**: `https://www.justgiving.com/fundraising/RussellMorbey-HackneyHalf?utm_medium=FR&utm_source=CL&utm_campaign=015`
- **Type**: `SECRET`
- **Scope**: `RUN_TIME`

**Add JAWG_ACCESS_TOKEN:**
- **Name**: `JAWG_ACCESS_TOKEN`
- **Value**: `your_jawg_access_token_here`
- **Type**: `SECRET`
- **Scope**: `RUN_TIME`

**Add STRAVA_CLIENT_ID:**
- **Name**: `STRAVA_CLIENT_ID`
- **Value**: `your_strava_client_id_here`
- **Type**: `SECRET`
- **Scope**: `RUN_TIME`

**Add STRAVA_CLIENT_SECRET:**
- **Name**: `STRAVA_CLIENT_SECRET`
- **Value**: `your_strava_client_secret_here`
- **Type**: `SECRET`
- **Scope**: `RUN_TIME`

**Add STRAVA_ACCESS_TOKEN:**
- **Name**: `STRAVA_ACCESS_TOKEN`
- **Value**: `your_strava_access_token_here`
- **Type**: `SECRET`
- **Scope**: `RUN_TIME`

**Add STRAVA_REFRESH_TOKEN:**
- **Name**: `STRAVA_REFRESH_TOKEN`
- **Value**: `your_strava_refresh_token_here`
- **Type**: `SECRET`
- **Scope**: `RUN_TIME`

**Add STRAVA_EXPIRES_AT:**
- **Name**: `STRAVA_EXPIRES_AT`
- **Value**: `your_strava_expires_at_here`
- **Type**: `SECRET`
- **Scope**: `RUN_TIME`

**Add STRAVA_EXPIRES_IN:**
- **Name**: `STRAVA_EXPIRES_IN`
- **Value**: `your_strava_expires_in_here`
- **Type**: `SECRET`
- **Scope**: `RUN_TIME`

**Add ENVIRONMENT:**
- **Name**: `ENVIRONMENT`
- **Value**: `production`
- **Type**: `PLAIN_TEXT`
- **Scope**: `RUN_TIME`

**Add PORT:**
- **Name**: `PORT`
- **Value**: `8080`
- **Type**: `PLAIN_TEXT`
- **Scope**: `RUN_TIME`

### **4. Optional: Automated Token Refresh Setup**

If you want automated Strava token refresh, add these additional secrets:

**Add DIGITALOCEAN_API_TOKEN:**
- **Name**: `DIGITALOCEAN_API_TOKEN`
- **Value**: `your_digitalocean_api_token_here`
- **Type**: `SECRET`
- **Scope**: `RUN_TIME`

**Add DIGITALOCEAN_APP_ID:**
- **Name**: `DIGITALOCEAN_APP_ID`
- **Value**: `your_digitalocean_app_id_here`
- **Type**: `SECRET`
- **Scope**: `RUN_TIME`

**To get these values:**
1. **DigitalOcean API Token**: Go to [API Tokens](https://cloud.digitalocean.com/account/api/tokens) → Generate New Token → Select "Write" scope
2. **App ID**: Found in your app's URL: `https://cloud.digitalocean.com/apps/[APP_ID]`

## 🔧 **Complete Environment Variables List**

Here's the complete list of all environment variables you need:

```bash
# API Security
STRAVA_API_KEY=your_strava_api_key_here
FUNDRAISING_API_KEY=your_fundraising_api_key_here

# Frontend Access Control
FRONTEND_ACCESS_TOKEN=your_frontend_access_token_here
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:8000,https://www.russellmorbey.co.uk,https://russellmorbey.co.uk

# JustGiving
JUSTGIVING_URL=https://www.justgiving.com/fundraising/RussellMorbey-HackneyHalf?utm_medium=FR&utm_source=CL&utm_campaign=015

# Jawg Maps
JAWG_ACCESS_TOKEN=your_jawg_access_token_here

# Strava API
STRAVA_CLIENT_ID=your_strava_client_id_here
STRAVA_CLIENT_SECRET=your_strava_client_secret_here

# Strava Tokens
STRAVA_ACCESS_TOKEN=your_strava_access_token_here
STRAVA_REFRESH_TOKEN=your_strava_refresh_token_here
STRAVA_EXPIRES_AT=your_strava_expires_at_here
STRAVA_EXPIRES_IN=your_strava_expires_in_here

# Environment
ENVIRONMENT=production
PORT=8080

# Automated Token Refresh (Optional)
DIGITALOCEAN_API_TOKEN=your_digitalocean_api_token_here
DIGITALOCEAN_APP_ID=your_digitalocean_app_id_here
```

## ✅ **Verification Steps**

### **1. Check All Secrets Are Set:**
1. Go to your app in DigitalOcean
2. Go to **Settings** → **App-Level Environment Variables**
3. Verify all 16+ environment variables are listed
4. Ensure all sensitive values are marked as `SECRET`

### **2. Test Your Deployment:**
```bash
# Test health endpoint
curl https://your-app.ondigitalocean.app/api/strava-integration/health

# Test API with API key
curl -H "X-API-Key: your_api_key_here" \
     https://your-app.ondigitalocean.app/api/strava-integration/feed?limit=5
```

### **3. Check Logs:**
1. Go to your app in DigitalOcean
2. Click **"Runtime Logs"**
3. Look for any environment variable errors
4. Verify the app starts successfully

## 🚨 **Security Best Practices**

### **✅ DO:**
- Set all sensitive values as `SECRET` type
- Use different keys for development and production
- Rotate keys regularly
- Monitor access logs

### **❌ DON'T:**
- Never commit real API keys to your repository
- Don't use the same keys for demo and production
- Don't share keys in documentation or chat
- Don't set sensitive values as `PLAIN_TEXT`

## 🔄 **Updating Secrets**

### **To Update a Secret:**
1. Go to **Settings** → **App-Level Environment Variables**
2. Click **"Edit"** next to the variable you want to update
3. Change the value
4. Click **"Save"**
5. The app will automatically restart with the new values

### **To Add a New Secret:**
1. Go to **Settings** → **App-Level Environment Variables**
2. Click **"Add Variable"**
3. Enter the name and value
4. Select the appropriate type (`SECRET` or `PLAIN_TEXT`)
5. Click **"Save"**

## 🎯 **Summary**

You now have:
- ✅ **16+ environment variables** properly configured
- ✅ **All secrets** marked as `SECRET` type
- ✅ **Frontend access control** configured
- ✅ **Automated token refresh** setup (optional)
- ✅ **Production-ready** configuration
- ✅ **Secure** secret management

**Your DigitalOcean app is now properly configured with all necessary secrets!** 🚀