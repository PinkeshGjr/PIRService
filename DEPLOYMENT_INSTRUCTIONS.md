# Quick Deployment Guide

## Step 1: Push to GitHub

Run these commands in Terminal:

```bash
cd /tmp/deploy
git init
git remote add origin https://github.com/PinkeshGjr/PIRService.git
git add .
git commit -m "Modified PIR Server - Disabled Privacy Pass authentication"
git branch -M main
git push -u origin main
```

**Note:** You may need to authenticate with GitHub. If you get an error, you can:
- Use a personal access token instead of password
- Or upload via GitHub Desktop
- Or use GitHub CLI: `gh auth login`

## Step 2: Deploy to Railway (Recommended - 5 minutes)

1. Go to [https://railway.app](https://railway.app)
2. Sign up with GitHub
3. Click "New Project"
4. Select "Deploy from GitHub repo"
5. Choose your `PIRService` repository
6. Railway will auto-detect the Dockerfile and deploy!
7. Wait 2-3 minutes for build to complete
8. Copy your public URL (e.g., `https://pirserver-production-xyz123.railway.app`)

## Step 3: Update iPhone App

1. Open SimpleURLFilter app
2. Go to Configuration
3. Set **PIR Server URL** to your Railway URL: `https://your-app.railway.app`
4. **Clear the Privacy Pass Issuer URL** (leave it completely empty!)
5. Keep Authentication Token as `AAAA`
6. Tap "Apply"

## Step 4: Test

- **Blocked URLs** (should be blocked): `example.com`, `example2.com`
- **Allowed URLs** (should work): `example1.com`, `google.com`, `apple.com`

## Alternative Platforms

If you prefer Render or Fly.io, see README.md for detailed instructions.

## Troubleshooting

- Make sure to **clear the Privacy Pass Issuer URL** field completely
- The server URL should be HTTPS (Railway provides this automatically)
- If you get "Error 10", check that the Privacy Pass Issuer URL is empty