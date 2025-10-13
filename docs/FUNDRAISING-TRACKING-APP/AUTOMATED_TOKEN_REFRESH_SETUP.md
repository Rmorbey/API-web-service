# 🤖 Automated Strava Token Refresh Setup

## 🎯 **Overview**

This guide sets up **fully automated Strava token refresh** for your production API. No more manual updates 4 times a day!

## 🚀 **How It Works**

### **Automatic Process:**
```
1. Strava token expires (every 6 hours)
2. Your API detects expiration
3. API calls Strava to refresh token
4. API automatically updates DigitalOcean secrets
5. DigitalOcean restarts your app with new tokens
6. Everything continues working seamlessly
```

## 🔧 **Setup Instructions**

### **Step 1: Get DigitalOcean API Token**

1. Go to [DigitalOcean API Tokens](https://cloud.digitalocean.com/account/api/tokens)
2. Click **"Generate New Token"**
3. Name: `API Token Refresh`
4. Scopes: Select **"Write"** (needed to update app secrets)
5. Copy the token (you'll need it for Step 3)

### **Step 2: Get Your App ID**

1. Go to your [DigitalOcean App Platform](https://cloud.digitalocean.com/apps)
2. Click on your API app
3. Look at the URL: `https://cloud.digitalocean.com/apps/[APP_ID]`
4. Copy the `[APP_ID]` from the URL

### **Step 3: Add Secrets to DigitalOcean**

In your DigitalOcean App Platform dashboard:

1. Go to **Settings** → **App-Level Environment Variables**
2. Add these new secrets:

```
DIGITALOCEAN_API_TOKEN = [Your API token from Step 1]
DIGITALOCEAN_APP_ID = [Your app ID from Step 2]
```

### **Step 4: Deploy Updated Code**

Your code is already updated! Just deploy:

```bash
git add .
git commit -m "Add automated token refresh"
git push origin main
```

DigitalOcean will automatically deploy the updated code.

## ✅ **Testing the Setup**

### **Test Token Refresh:**

1. **Check logs** in DigitalOcean App Platform
2. **Look for messages** like:
   ```
   🔄 NEW STRAVA TOKENS - TRIGGERING AUTOMATED UPDATE:
   ✅ DigitalOcean secrets updated successfully
   🔄 App will restart automatically with new tokens
   ```

### **Verify Secrets Updated:**

1. Go to **Settings** → **App-Level Environment Variables**
2. Check that `STRAVA_ACCESS_TOKEN` and `STRAVA_REFRESH_TOKEN` have new values
3. Check the timestamps to confirm they were updated recently

## 🎯 **What Happens Now**

### **Fully Automated:**
- ✅ **Token refresh** - Happens automatically every 6 hours
- ✅ **Secret updates** - DigitalOcean secrets updated automatically
- ✅ **App restart** - DigitalOcean restarts your app with new tokens
- ✅ **Zero downtime** - Your API continues working seamlessly

### **No Manual Intervention Needed:**
- ❌ **No manual updates** - Everything is automatic
- ❌ **No monitoring required** - System handles itself
- ❌ **No downtime** - Seamless token refresh

## 🔍 **Monitoring & Troubleshooting**

### **Check Logs:**
```bash
# In DigitalOcean App Platform
1. Go to your app
2. Click "Runtime Logs"
3. Look for token refresh messages
```

### **Common Issues:**

#### **Issue: "DIGITALOCEAN_API_TOKEN not set"**
**Solution:** Make sure you added the API token as a secret in DigitalOcean

#### **Issue: "Failed to update DigitalOcean secrets"**
**Solution:** Check that your API token has "Write" permissions

#### **Issue: "DIGITALOCEAN_APP_ID not set"**
**Solution:** Make sure you added the correct app ID as a secret

### **Fallback Behavior:**
If automated update fails, the system will:
1. **Log the new tokens** to console and file
2. **Continue working** with new tokens in memory
3. **Alert you** to update secrets manually (as backup)

## 🎉 **Benefits**

### **✅ Fully Automated:**
- **No manual intervention** - Works 24/7
- **No missed updates** - Always has fresh tokens
- **No downtime** - Seamless operation

### **✅ Production Ready:**
- **Secure** - Uses DigitalOcean API with proper authentication
- **Reliable** - Built-in error handling and fallbacks
- **Scalable** - Works with any number of app instances

### **✅ Cost Effective:**
- **No additional services** - Uses existing DigitalOcean infrastructure
- **No extra costs** - Just uses your existing API token
- **No maintenance** - Set it and forget it

## 🚀 **You're All Set!**

Your Strava token refresh is now **fully automated**! The system will:

1. **Automatically refresh tokens** every 6 hours
2. **Update DigitalOcean secrets** automatically
3. **Restart your app** with new tokens
4. **Continue working** without any manual intervention

**No more manual updates 4 times a day!** 🎯
