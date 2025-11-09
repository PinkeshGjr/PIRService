# PIR Server - Modified for URL Filtering

This is a modified version of Apple's PIR (Private Information Retrieval) Server, modified to **skip Privacy Pass authentication** for easier testing and development.

## What Was Modified

- **Disabled Privacy Pass authentication** - The server no longer requires Privacy Pass tokens
- **Modified source files**:
  - `Sources/PIRService/main.swift` - Changed to pass `nil` for `PrivacyPassState`
  - `Sources/PIRService/ReloadService.swift` - Made `privacyPassState` optional

## How to Deploy

### Option 1: Railway (Easiest)

1. **Fork/Clone this repository**
2. **Sign up at [railway.app](https://railway.app)** (free with GitHub)
3. **Create a new project** → Deploy from GitHub repo
4. **Select this repository**
5. **Railway will automatically detect the Dockerfile and deploy!**
6. **Get your public URL** (e.g., `https://your-app.railway.app`)

### Option 2: Render (render.com)

1. **Sign up at render.com**
2. **Create Web Service** → Connect GitHub
3. **Select this repository**
4. **Set build command:** `docker build -t pir-server .`
5. **Set start command:** `docker run -p 8080:8080 pir-server`

### Option 3: Fly.io

1. **Install flyctl**: `curl -L https://fly.io/install.sh | sh`
2. **Sign up**: `fly auth signup`
3. **Deploy**: `fly deploy`
4. **Get URL**: `fly info`

## iOS App Configuration

Update your SimpleURLFilter iOS app configuration:

- **PIR Server URL**: `https://your-deployed-url.railway.app` (or your platform's URL)
- **PIR Privacy Pass Issuer URL**: **LEAVE EMPTY**
- **Authentication Token**: `AAAA`

## Blocked URLs

The server blocks these URLs (for testing):
- `example.com`
- `example2.com` through `example9.com`
- `example10.com/resource?query=bugs`

Allowed URLs (should work):
- `example1.com` (intentionally not blocked)
- `google.com`
- `apple.com`

## Local Development

To run locally with Docker:

```bash
docker build -t pir-server .
docker run -p 8080:8080 pir-server
```

## Architecture

- **PIR Server**: Handles URL filtering requests using homomorphic encryption
- **Database**: Contains blocked URL list encrypted in PIR format
- **No Authentication**: Skips Privacy Pass for easier testing

## License

See LICENSE.txt for details. Based on Apple's sample code.