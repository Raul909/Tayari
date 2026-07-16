#!/bin/bash
set -e

echo "🌊 Tayari Frontend Deployment (Cloudflare Pages)"
echo "------------------------------------------------"

# Prompt for the Hugging Face backend URL
read -p "Enter your Hugging Face Space URL (e.g., https://raul909-tayari.hf.space): " HF_URL

# Remove trailing slash if present
HF_URL=${HF_URL%/}

if [[ ! "$HF_URL" =~ ^https:// ]]; then
    echo "❌ Error: URL must start with https://"
    exit 1
fi

echo "✅ Backend URL set to: $HF_URL"
echo ""

echo "Deploying Frontend to Cloudflare Pages..."
cd frontend

echo "Building static frontend with NEXT_PUBLIC_API_URL=$HF_URL..."
NEXT_PUBLIC_API_URL="$HF_URL" npm run build

echo "Uploading to Cloudflare Pages..."
npx wrangler pages deploy out --project-name tayari

echo "------------------------------------------------"
echo "✅ DEPLOYMENT COMPLETE! 🌊"
echo "Frontend should now be available on your Cloudflare Pages tayari.pages.dev domain."
