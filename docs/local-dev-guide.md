# Local development with APIM + DevTunnel

## Purpose
Use APIM as the ingress while routing backend traffic to your local service through a DevTunnel.

## Prerequisites
- Docker Desktop (or local backend on port 8000)
- DevTunnel CLI authenticated and available in PATH

## One-time setup
Run:

```powershell
.\scripts\devtunnel-setup.ps1
```

Optional custom port:

```powershell
.\scripts\devtunnel-setup.ps1 -Port 8000
```

What this does:
- Creates a tunnel with `devtunnel create --allow-anonymous`
- Parses the auto-generated **Tunnel ID** from CLI output
- Stores that ID in `.devtunnel-id` (local file, ignored by git)
- Creates the tunnel port mapping for the chosen port
- Prints the tunnel URL to copy into APIM Named Value `backend-url`

## Daily usage
1. Start local services (for example `docker compose up --build`).
2. Start the tunnel host:

```powershell
.\scripts\devtunnel-start.ps1
```

This reads `.devtunnel-id` and runs `devtunnel host {tunnel-id}`.

## APIM configuration
- Set APIM Named Value `backend-url` to the URL printed by setup.
- Keep `DEVTUNNEL_URL` in `.env` aligned with the same value when needed locally.

## Troubleshooting
- **Missing `.devtunnel-id`**: run `.\scripts\devtunnel-setup.ps1` first.
- **Port mismatch**: rerun setup with the correct `-Port` value.
