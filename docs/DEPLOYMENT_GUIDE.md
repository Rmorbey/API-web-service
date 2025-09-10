# DigitalOcean App Platform Deployment Guide

## 🚀 Deploying Your FastAPI Service to DigitalOcean

This guide will help you deploy your FastAPI fundraising tracking app to DigitalOcean App Platform at `www.russellmorbey.co.uk/api/fundraising-tracking-app/`

## 📋 Prerequisites

1. **DigitalOcean Account** with App Platform access
2. **GitHub Repository** with your code
3. **Domain** (www.russellmorbey.co.uk) configured in DigitalOcean
4. **Strava API Credentials** ready

## 🔧 Step 1: Prepare Your Repository

### 1.1 Push Your Code to GitHub
```bash
# Initialize git if not already done
git init
git add .
git commit -m "Initial commit with FastAPI fundraising tracking app"

# Add your GitHub repository as remote
git remote add origin https://github.com/your-username/API-web-service.git
git push -u origin main
```

### 1.2 Update App Platform Configuration
Edit `.do/app.yaml` and update the GitHub repository details:
```yaml
github:
  repo: your-username/API-web-service  # Update this
  branch: main
```

## 🌐 Step 2: Configure DigitalOcean App Platform

### 2.1 Create New App
1. Go to [DigitalOcean App Platform](https://cloud.digitalocean.com/apps)
2. Click **"Create App"**
3. Choose **"GitHub"** as source
4. Select your repository: `your-username/API-web-service`
5. Choose branch: `main`

### 2.2 Configure Service
1. **Name**: `fundraising-tracking-api`
2. **Source Directory**: `/` (root)
3. **Build Command**: Leave empty (uses Dockerfile)
4. **Run Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. **Environment**: `Python`
6. **Instance Size**: `Basic XXS` (cost-effective for personal use)

### 2.3 Configure Routes
- **Path**: `/api/fundraising-tracking-app`
- **Port**: `8080`

### 2.4 Set Environment Variables
In the App Platform dashboard, add these environment variables:

#### Required Secrets (mark as SECRET):
- `STRAVA_CLIENT_ID` = your_strava_client_id
- `STRAVA_CLIENT_SECRET` = your_strava_client_secret
- `STRAVA_ACCESS_TOKEN` = your_oauth_access_token
- `STRAVA_REFRESH_TOKEN` = your_oauth_refresh_token
- `STRAVA_EXPIRES_AT` = your_token_expires_at

#### Regular Variables:
- `STRAVA_REDIRECT_URI` = `https://www.russellmorbey.co.uk/api/fundraising-tracking-app/auth/strava/callback`
- `PORT` = `8080`

## 🔐 Step 3: Get Production Strava Tokens

### 3.1 Update Strava App Settings
1. Go to [Strava API Settings](https://www.strava.com/settings/api)
2. Update your app's **Authorization Callback Domain** to: `russellmorbey.co.uk`
3. Note your **Client ID** and **Client Secret**

### 3.2 Get OAuth Tokens
Use the local script to get production tokens:
```bash
# Update the redirect URI in your local .env
STRAVA_REDIRECT_URI=https://www.russellmorbey.co.uk/api/fundraising-tracking-app/auth/strava/callback

# Run the OAuth flow
python3 test_oauth_token.py
```

## 🚀 Step 4: Deploy

### 4.1 Deploy via App Platform
1. Click **"Create Resources"** in DigitalOcean
2. Wait for deployment to complete (5-10 minutes)
3. Your API will be available at: `https://www.russellmorbey.co.uk/api/fundraising-tracking-app/`

### 4.2 Test Deployment
```bash
# Test health endpoint
curl https://www.russellmorbey.co.uk/api/fundraising-tracking-app/health

# Test root endpoint
curl https://www.russellmorbey.co.uk/api/fundraising-tracking-app/
```

## 🔄 Step 5: Update Your React Frontend

### 5.1 Update API Base URL
In your React app, update the API base URL:
```javascript
// Change from:
const API_BASE_URL = 'http://localhost:8000';

// To:
const API_BASE_URL = 'https://www.russellmorbey.co.uk/api/fundraising-tracking-app';
```

### 5.2 Update Strava Integration
Update your React components to use the production API:
```javascript
// In your React components
const response = await fetch('https://www.russellmorbey.co.uk/api/fundraising-tracking-app/activities', {
  headers: {
    'Authorization': `Bearer ${accessToken}`
  }
});
```

## 📊 Step 6: Monitor and Maintain

### 6.1 Health Monitoring
- DigitalOcean provides built-in health checks
- Monitor logs in the App Platform dashboard
- Set up alerts for downtime

### 6.2 Token Refresh
- Strava tokens expire every 6 hours
- Implement automatic token refresh in your app
- Monitor token expiration and refresh as needed

### 6.3 Scaling
- Start with Basic XXS (512MB RAM, 1 vCPU)
- Scale up if needed based on usage
- Consider Basic XS (1GB RAM, 1 vCPU) for better performance

## 🔧 Troubleshooting

### Common Issues:

1. **CORS Errors**
   - Ensure your domain is in the CORS allow_origins list
   - Check that requests are coming from the correct domain

2. **Token Expired**
   - Use the OAuth flow to get fresh tokens
   - Update environment variables in App Platform

3. **Build Failures**
   - Check Dockerfile syntax
   - Ensure all dependencies are in requirements.txt
   - Review build logs in App Platform dashboard

4. **Route Not Found**
   - Verify the route path is `/api/fundraising-tracking-app`
   - Check that the app is deployed and running

## 💰 Cost Estimation

- **Basic XXS**: ~$5/month
- **Basic XS**: ~$12/month
- **Custom Domain**: Free (if you own the domain)

## 🎉 Success!

Once deployed, your API will be available at:
- **Health Check**: `https://www.russellmorbey.co.uk/api/fundraising-tracking-app/health`
- **API Docs**: `https://www.russellmorbey.co.uk/api/fundraising-tracking-app/docs`
- **Activities**: `https://www.russellmorbey.co.uk/api/fundraising-tracking-app/activities`

Your React frontend can now make requests to your production API!
