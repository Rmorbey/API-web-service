# 🔐 DigitalOcean App Platform Secrets Setup Guide

## 📋 **Your Environment Variables**

Based on your `.env` file, here are all the secrets you need to set in DigitalOcean:

### **API Security Keys:**
- `STRAVA_API_KEY` = `your_strava_api_key_here`
- `FUNDRAISING_API_KEY` = `your_fundraising_api_key_here`

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

## 🚀 **Step-by-Step Setup in DigitalOcean**

### **1. Deploy Your App:**
```bash
# Push your code to GitHub
git add .
git commit -m "Production deployment ready with secrets configuration"
git push origin main
```

### **2. Create App in DigitalOcean:**
1. Go to [DigitalOcean App Platform](https://cloud.digitalocean.com/apps)
2. Click **"Create App"**
3. Connect your GitHub repository
4. Select your repository: `API-web-service`
5. DigitalOcean will detect the `.do/app.yaml` file automatically

### **3. Set Environment Variables as Secrets:**
1. In your app dashboard, go to **Settings** → **App-Level Environment Variables**
2. Add each secret one by one:

#### **Add STRAVA_API_KEY:**
- **Name**: `STRAVA_API_KEY`
- **Value**: `your_strava_api_key_here`
- **Type**: `SECRET` (not plain text)
- **Scope**: `RUN_TIME`

#### **Add FUNDRAISING_API_KEY:**
- **Name**: `FUNDRAISING_API_KEY`
- **Value**: `your_fundraising_api_key_here`
- **Type**: `SECRET`
- **Scope**: `RUN_TIME`

#### **Add JUSTGIVING_URL:**
- **Name**: `JUSTGIVING_URL`
- **Value**: `https://www.justgiving.com/fundraising/RussellMorbey-HackneyHalf?utm_medium=FR&utm_source=CL&utm_campaign=015`
- **Type**: `SECRET`
- **Scope**: `RUN_TIME`

#### **Add JAWG_ACCESS_TOKEN:**
- **Name**: `JAWG_ACCESS_TOKEN`
- **Value**: `your_jawg_access_token_here`
- **Type**: `SECRET`
- **Scope**: `RUN_TIME`

#### **Add STRAVA_CLIENT_ID:**
- **Name**: `STRAVA_CLIENT_ID`
- **Value**: `your_strava_client_id_here`
- **Type**: `SECRET`
- **Scope**: `RUN_TIME`

#### **Add STRAVA_CLIENT_SECRET:**
- **Name**: `STRAVA_CLIENT_SECRET`
- **Value**: `your_strava_client_secret_here`
- **Type**: `SECRET`
- **Scope**: `RUN_TIME`

#### **Add STRAVA_ACCESS_TOKEN:**
- **Name**: `STRAVA_ACCESS_TOKEN`
- **Value**: `your_strava_access_token_here`
- **Type**: `SECRET`
- **Scope**: `RUN_TIME`

#### **Add STRAVA_REFRESH_TOKEN:**
- **Name**: `STRAVA_REFRESH_TOKEN`
- **Value**: `your_strava_refresh_token_here`
- **Type**: `SECRET`
- **Scope**: `RUN_TIME`

#### **Add STRAVA_EXPIRES_AT:**
- **Name**: `STRAVA_EXPIRES_AT`
- **Value**: `your_strava_expires_at_here`
- **Type**: `SECRET`
- **Scope**: `RUN_TIME`

#### **Add STRAVA_EXPIRES_IN:**
- **Name**: `STRAVA_EXPIRES_IN`
- **Value**: `your_strava_expires_in_here`
- **Type**: `SECRET`
- **Scope**: `RUN_TIME`

### **4. Deploy Your App:**
1. Click **"Create Resources"** or **"Deploy"**
2. DigitalOcean will build and deploy your app
3. Wait for deployment to complete (5-10 minutes)

### **5. Test Your Deployment:**
1. Go to your app's URL (e.g., `https://your-app-name.ondigitalocean.app`)
2. Test the health endpoint: `https://your-app-name.ondigitalocean.app/api/strava-integration/health`
3. Test the API: `https://your-app-name.ondigitalocean.app/api/strava-integration/feed?limit=5`

## 🔒 **Security Notes**

### **✅ What's Secure:**
- All your API keys are stored as encrypted secrets in DigitalOcean
- Secrets are never exposed in your repository
- Secrets are never visible in logs
- Only your app can access these secrets at runtime

### **✅ What's Safe to Commit:**
- `env.production` (template with placeholder values)
- `.do/app.yaml` (configuration file)
- All your application code

## 🎯 **Quick Verification**

### **Check Your App is Running:**
```bash
# Replace with your actual app URL
curl https://your-app-name.ondigitalocean.app/api/strava-integration/health
```

### **Expected Response:**
```json
{
  "project": "strava-integration",
  "status": "healthy",
  "timestamp": "2025-01-02T...",
  "strava_configured": true,
  "jawg_configured": true,
  "cache_status": "active"
}
```

## 🚨 **Important Reminders**

1. **Never commit real API keys** to your repository
2. **Always use SECRET type** in DigitalOcean (not plain text)
3. **Test your deployment** after setting secrets
4. **Keep your local `.env` file** for development
5. **Update secrets** if you regenerate API keys

## 🎉 **You're All Set!**

Your production deployment is now ready with:
- ✅ All secrets configured securely
- ✅ Production-optimized Docker image
- ✅ Single worker for rate-limited APIs
- ✅ Health checks and monitoring
- ✅ Cache backups for data recovery

**Cost**: ~$5/month on DigitalOcean Basic plan
