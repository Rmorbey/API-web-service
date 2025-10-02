# API Security Best Practices

## 🚨 **Critical Security Issue Fixed**

### **Problem Identified:**
- **API keys were exposed** in client-side HTML files
- **Keys were visible** to anyone viewing the demo pages
- **Keys were committed** to the repository
- **This is a major security vulnerability**

### **What Was Wrong:**
```javascript
// ❌ WRONG - API key exposed in client-side code
const response = await fetch('/api/endpoint', {
    headers: {
        'X-API-Key': 'your_api_key_here'  // VISIBLE TO EVERYONE!
    }
});
```

## ✅ **Proper Security Solution**

### **1. Demo Endpoints (No API Key Required)**
Created separate demo endpoints that don't require authentication:

```python
# ✅ CORRECT - Demo endpoint (no API key needed)
@router.get("/demo/data", response_model=FundraisingDataResponse)
async def get_fundraising_data_demo() -> FundraisingDataResponse:
    """Get fundraising data for demo page (no API key required)"""
    # ... implementation
```

### **2. Protected Endpoints (API Key Required)**
Keep the original endpoints protected for production use:

```python
# ✅ CORRECT - Protected endpoint (API key required)
@router.get("/data", response_model=FundraisingDataResponse)
async def get_fundraising_data(api_key: str = Depends(verify_api_key)) -> FundraisingDataResponse:
    """Get fundraising data (requires API key)"""
    # ... implementation
```

### **3. Client-Side Code (No API Keys)**
```javascript
// ✅ CORRECT - No API key in client-side code
const response = await fetch('/api/fundraising/demo/data');
```

## 🔐 **API Key Security Rules**

### **NEVER Do This:**
- ❌ Put API keys in client-side code
- ❌ Commit API keys to repositories
- ❌ Expose API keys in HTML/JavaScript
- ❌ Share API keys in documentation
- ❌ Use the same key for demo and production

### **ALWAYS Do This:**
- ✅ Store API keys in environment variables
- ✅ Use different keys for different environments
- ✅ Rotate keys regularly
- ✅ Use demo endpoints for public demos
- ✅ Keep production keys secret

## 🏗️ **Architecture Overview**

### **Demo Pages (Public Access):**
```
Frontend Demo → /api/*/demo/* → No Authentication Required
```

### **Production API (Protected):**
```
Frontend App → /api/*/endpoint → API Key Required
```

## 📁 **File Structure**

### **Demo Files (No API Keys):**
- `examples/fundraising-demo.html` - Uses `/demo/data` and `/demo/donations`
- `examples/strava-react-demo-clean.html` - Uses `/demo/feed` and `/demo/map-tiles`

### **Production Files (API Keys in .env):**
- `.env` - Contains actual API keys (not committed)
- `.env.example` - Contains placeholder keys (committed)
- `env.production` - Contains production placeholders (committed)

## 🔧 **Environment Variables**

### **Development (.env):**
```bash
STRAVA_API_KEY=your_actual_strava_key_here
FUNDRAISING_API_KEY=your_actual_fundraising_key_here
```

### **Production (DigitalOcean Secrets):**
```bash
STRAVA_API_KEY=production_strava_key
FUNDRAISING_API_KEY=production_fundraising_key
```

## 🚀 **Deployment Security**

### **DigitalOcean App Platform:**
1. **Never commit real API keys** to repository
2. **Set secrets in DigitalOcean dashboard**:
   - Go to App → Settings → App-Level Environment Variables
   - Add each API key as a secret
3. **Use environment variables** in code:
   ```python
   API_KEY = os.getenv("STRAVA_API_KEY")
   if not API_KEY:
       raise ValueError("STRAVA_API_KEY environment variable is required")
   ```

## 🛡️ **Security Checklist**

### **Before Deployment:**
- [ ] No API keys in client-side code
- [ ] No API keys in committed files
- [ ] Demo endpoints work without authentication
- [ ] Production endpoints require API keys
- [ ] Environment variables properly configured
- [ ] Secrets set in deployment platform

### **After Deployment:**
- [ ] Test demo pages work without API keys
- [ ] Test production endpoints require API keys
- [ ] Verify keys are not visible in browser
- [ ] Confirm keys are not in repository

## 📚 **Additional Resources**

- [FastAPI Security Documentation](https://fastapi.tiangolo.com/tutorial/security/)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [DigitalOcean App Platform Secrets](https://docs.digitalocean.com/products/app-platform/how-to/use-secrets/)

## 🎯 **Summary**

**The fix ensures:**
1. **Demo pages work** without exposing API keys
2. **Production APIs remain secure** with proper authentication
3. **API keys stay secret** and are never committed
4. **Best practices are followed** for API security

**This approach provides:**
- ✅ Public demo access (no API keys needed)
- ✅ Secure production access (API keys required)
- ✅ No security vulnerabilities
- ✅ Clean separation of concerns
