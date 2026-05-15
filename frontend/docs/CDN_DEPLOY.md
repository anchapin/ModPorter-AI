# Cloudflare Pages Configuration for Portkit Frontend

## Build Settings
- **Build command**: `pnpm run build`
- **Build output directory**: `dist`
- **Node.js version**: `20`

## Routing
All routes are handled by `dist/_redirects` which rewrites `/*` to `/index.html` with a 200 status, enabling client-side SPA routing.

## Environment Variables (set in Cloudflare Pages dashboard)
| Variable | Description |
|----------|-------------|
| `VITE_API_URL` | Backend API URL (e.g., `https://api.portkit.dev`) |
| `VITE_API_BASE_URL` | Base URL for API (e.g., `https://api.portkit.dev`) |
| `VITE_WS_URL` | WebSocket URL (e.g., `wss://api.portkit.dev`) |

## Cache Headers
- `/_headers` file configures security headers for all routes
- Static assets under `/assets/*` are cached for 1 year (immutable)
- HTML files have `Cache-Control: no-cache` to ensure freshness

## Deploy Steps
1. Connect your GitHub repository to [Cloudflare Pages](https://pages.cloudflare.com/)
2. Select the `frontend` directory as the project root
3. Set build command: `pnpm run build`
4. Set build output directory: `dist`
5. Add environment variables from `.env.example`
6. Click **Deploy**

## Local Preview
```bash
cd frontend
pnpm install --frozen-lockfile
pnpm run build
# Serve dist/ with any static server, e.g.:
npx serve dist
```