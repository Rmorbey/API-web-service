# 🔐 DigitalOcean Secrets Setup Guide

## 📋 **Required Environment Variables**

Set these as **SECRET** type in DigitalOcean App Platform:

### **API Security Keys:**
- `ACTIVITY_API_KEY` = `your_activity_api_key_here`
- `FUNDRAISING_API_KEY` = `your_fundraising_api_key_here`

### **JustGiving Configuration:**
- `JUSTGIVING_URL` = `https://www.justgiving.com/fundraising/RussellMorbey-HackneyHalf?utm_medium=FR&utm_source=CL&utm_campaign=015`

### **Jawg Maps Configuration:**
- `JAWG_ACCESS_TOKEN` = `your_jawg_access_token_here`

### **Google Sheets API Configuration (for GPX Import):**
- `GOOGLE_SHEETS_SPREADSHEET_ID` = `your_google_sheets_id_here`
- `GOOGLE_SHEETS_CREDENTIALS_FILE` = `path/to/credentials.json`
- `GOOGLE_SHEETS_TOKEN_FILE` = `path/to/token.json`

### **Activity Cache Configuration:**
- `ACTIVITY_CACHE_HOURS` = `8`

### **Environment Configuration:**
- `ENVIRONMENT` = `production`
- `PORT` = `8080`
- `TZ` = `Europe/London`

### **Supabase Configuration:**
- `SUPABASE_URL` = `your_supabase_project_url`
- `SUPABASE_ANON_KEY` = `your_supabase_anonymous_key`
- `SUPABASE_SERVICE_KEY` = `your_supabase_service_role_key`

### **Automated Token Refresh (Optional):**
- `DIGITALOCEAN_API_TOKEN` = `your_digitalocean_api_token_here`
- `DIGITALOCEAN_APP_ID` = `your_digitalocean_app_id_here`

## 🚀 **Setup Steps**

### **1. Deploy Your App:**
```bash
git add .
git commit -m "Add production deployment configuration"
git push origin main
```

### **2. Create App in DigitalOcean:**
1. Go to [DigitalOcean App Platform](https://cloud.digitalocean.com/apps)
2. Click **"Create App"**
3. Connect your GitHub repository: `russellmorbey/API-web-service`
4. DigitalOcean will detect `.do/app.yaml` automatically

### **3. Set Environment Variables:**
1. Go to **Settings** → **App-Level Environment Variables**
2. Click **"Edit"**
3. Add each variable:
   - **Name**: Variable name (e.g., `ACTIVITY_API_KEY`)
   - **Value**: Your actual value
   - **Type**: `SECRET` (for sensitive data) or `PLAIN_TEXT` (for non-sensitive)
   - **Scope**: `RUN_TIME`

### **4. Google Sheets API Setup**

For GPX activity import via Google Sheets:

**Get DigitalOcean API Token:**
1. Go to [API Tokens](https://cloud.digitalocean.com/account/api/tokens)
2. Generate New Token → Select "Write" scope

**Get App ID:**
1. Found in your app's URL: `https://cloud.digitalocean.com/apps/[APP_ID]`

## ✅ **Verification Steps**

### **1. Check All Secrets Are Set:**
1. Go to **Settings** → **App-Level Environment Variables**
2. Verify all 16+ environment variables are listed
3. Ensure all sensitive values are marked as `SECRET`

### **2. Test Your Deployment:**
```bash
# Test health endpoint
curl https://your-app.ondigitalocean.app/api/activity-integration/health

# Test API with API key
curl -H "X-API-Key: your_api_key_here" \
     https://your-app.ondigitalocean.app/api/activity-integration/feed?limit=5
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