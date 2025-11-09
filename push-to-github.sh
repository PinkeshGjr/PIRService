#!/bin/bash

# Navigate to the deploy directory
cd /tmp/deploy

# Initialize git if not already done
if [ ! -d .git ]; then
    git init
fi

# Add GitHub remote (replace with your actual repo URL)
git remote add origin https://github.com/PinkeshGjr/PIRService.git

# Add all files
git add .

# Commit
git commit -m "Modified PIR Server - Disabled Privacy Pass authentication for testing

- Modified main.swift to pass nil for PrivacyPassState
- Modified ReloadService.swift to handle optional privacyPassState
- Added Dockerfile for cloud deployment
- Added README with deployment instructions
- Ready to deploy to Railway/Render/Fly.io"

# Push to main branch (you may need to create the main branch first)
git branch -M main
git push -u origin main

echo "Code pushed to GitHub successfully!"
