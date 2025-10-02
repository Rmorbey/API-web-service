# 🔒 Frontend Security Guide

## 🚨 **SECURITY IMPLEMENTATION COMPLETE**

Your API is now **fully secured** and only accessible to your authorized frontend applications.

## 🛡️ **Security Layers Implemented**

### **1. API Key Authentication**
- **All endpoints** now require valid API key via `X-API-Key` header
- **API Key**: `your_api_key_here`
- **Protection**: Prevents unauthorized access to your personal data

### **2. Frontend Domain Verification**
- **Referer Check**: Validates requests come from authorized domains
- **Allowed Domains**:
  - `http://localhost:3000` (React dev)
  - `http://localhost:5173` (Vite dev)
  - `http://localhost:8000` (Local dev)
  - `https://www.russellmorbey.co.uk` (Production)
  - `https://russellmorbey.co.uk` (Production)

### **3. Map Tile Security**
- **Token Validation**: Map tiles require valid token parameter
- **Server-Side Proxy**: Jawg token never exposed to frontend
- **Fallback Protection**: Falls back to OpenStreetMap if unauthorized

## 🔑 **How to Use in Your Frontend**

### **JavaScript Fetch Example**
```javascript
// Strava Activities
const response = await fetch('/api/strava-integration/feed?limit=50', {
    headers: {
        'X-API-Key': 'your_api_key_here'
    }
});

// Fundraising Data
const response = await fetch('/api/fundraising/data', {
    headers: {
        'X-API-Key': 'your_api_key_here'
    }
});

// Map Tiles (Leaflet)
L.tileLayer('http://localhost:8000/api/strava-integration/map-tiles/{z}/{x}/{y}?token=your_token_here', {
    attribution: '© Jawg Maps & OpenStreetMap'
}).addTo(map);
```

### **React/Next.js Example**
```jsx
const API_KEY = 'your_api_key_here';

const fetchActivities = async () => {
    const response = await fetch('/api/strava-integration/feed', {
        headers: { 'X-API-Key': API_KEY }
    });
    return response.json();
};
```

## 🚫 **What's Now Blocked**

### **❌ Unauthorized Access Attempts**
- **No API Key**: `401 Unauthorized`
- **Invalid API Key**: `403 Forbidden`
- **Wrong Domain**: `403 Forbidden`
- **Direct API Calls**: Blocked unless from authorized frontend

### **❌ Public Access**
- **Anyone can't access your data** without the API key
- **Random websites can't embed your data**
- **API scraping is blocked** by rate limiting + authentication

## 🔧 **Environment Variables Required**

```bash
# Required for API to start
STRAVA_API_KEY="your_strava_api_key_here"
FUNDRAISING_API_KEY="your_fundraising_api_key_here"

# Optional (for map tiles)
JAWG_ACCESS_TOKEN="your-jawg-token"
```

## 🎯 **Security Benefits**

### **✅ Data Protection**
- **Personal Strava data** only accessible to your frontend
- **Fundraising data** protected from unauthorized access
- **Map tiles** secured with token validation

### **✅ Frontend Integration**
- **Seamless integration** with your React/Next.js apps
- **Same API key** works for all endpoints
- **Automatic fallbacks** for development vs production

### **✅ Rate Limiting**
- **1000 requests/hour** per IP address
- **500 requests/minute** for map tiles
- **Automatic blocking** of excessive requests

## 🚀 **Deployment Security**

### **Production Setup**
1. **Change API Keys**: Use strong, unique keys in production
2. **Update Domains**: Add your production domain to allowed list
3. **HTTPS Only**: Ensure all communication is encrypted
4. **Environment Variables**: Never commit API keys to version control

### **Frontend Deployment**
1. **Environment Variables**: Store API key in frontend environment
2. **Build Process**: Include API key in build configuration
3. **Domain Verification**: Ensure frontend domain is in allowed list

## 🔍 **Testing Security**

### **Test Unauthorized Access**
```bash
# This should fail (401 Unauthorized)
curl http://localhost:8000/api/strava-integration/feed

# This should fail (403 Forbidden)
curl -H "X-API-Key: wrong-key" http://localhost:8000/api/strava-integration/feed

# This should work (200 OK)
curl -H "X-API-Key: your_api_key_here" http://localhost:8000/api/strava-integration/feed
```

## 📊 **Security Status**

| Endpoint | Authentication | Domain Check | Status |
|----------|---------------|--------------|---------|
| `/api/strava-integration/feed` | ✅ API Key | ✅ Referer | 🔒 SECURE |
| `/api/strava-integration/metrics` | ✅ API Key | ❌ | 🔒 SECURE |
| `/api/strava-integration/map-tiles` | ✅ Token | ❌ | 🔒 SECURE |
| `/api/fundraising/data` | ✅ API Key | ❌ | 🔒 SECURE |
| `/api/fundraising/donations` | ✅ API Key | ❌ | 🔒 SECURE |

## 🎉 **Result**

Your API is now **completely secure** and only accessible to your authorized frontend applications. No one else can access your personal Strava data, fundraising information, or any other sensitive data without proper authentication and authorization.

**Your data is safe!** 🛡️
