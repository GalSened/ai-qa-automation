# Deployment Guide

## GitHub Pages Deployment

### Option 1: Automatic GitHub Actions (Recommended)

1. **Create GitHub Repository:**

   ```bash
   # On your local machine
   git init
   git add .
   git commit -m "Initial commit: AI QA Automation System"
   git branch -M main
   git remote add origin https://github.com/yourusername/ai-qa-automation.git
   git push -u origin main
   ```
2. **Enable GitHub Pages:**

   - Go to your repository settings
   - Navigate to "Pages" section
   - Source: "GitHub Actions"
   - The workflow will automatically deploy on every push to main
3. **Your site will be available at:**
   `https://yourusername.github.io/ai-qa-automation/`

### Option 2: Manual GitHub Pages

1. **Build locally:**

   ```bash
   npm run build
   ```
2. **Deploy to gh-pages branch:**

   ```bash
   npm install -g gh-pages
   gh-pages -d dist
   ```

## Vercel Deployment (Alternative)

1. **Connect to Vercel:**

   - Go to [vercel.com](https://vercel.com)
   - Import your GitHub repository
   - Vercel will auto-detect Vite and deploy
2. **Custom domain (optional):**

   - Add your domain in Vercel dashboard
   - Update DNS records as instructed

## Local Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Docker System (Separate)

The AI QA automation Docker system is separate from this web demo:

```bash
# Run the actual AI system locally
docker-compose up --build

# Access services:
# - QA Analyzer: http://localhost:8000
# - Playwright MCP: http://localhost:8001
# - Ollama: http://localhost:11434
```

## Environment Variables

For production deployment, no environment variables are needed for the demo.
For the actual Docker system, copy `.env.example` to `.env` and configure as needed.
