# Local E2E development with APIM + DevTunnel

## 1) Prerequisites

- Docker Desktop installed and running
- DevTunnel CLI installed and authenticated (`devtunnel user login`)
- Azure CLI authenticated (`az login`)
- Node.js 22+ (for Angular local dev server)
- `.env` configured from `.env.example`
- Entra ID app is multi-tenant with Client ID `9dfbf018-d41b-4579-8b6c-e58d1a9a52be`

## 2) One-time setup

1. Create and configure the persistent tunnel:
   - `.\scripts\devtunnel-setup.ps1`
2. Copy the DevTunnel URL printed by the script.
3. In Azure Portal:
   - Go to **API Management** → `calabriomafpoc-apim` → **Named values**
   - Create or update `backend-url` with the DevTunnel URL (example: `https://xxxxx.devtunnels.ms`)
4. Configure APIM API operations:
   - `POST /chat`
   - `GET /health`
   - `GET /ready`
   - Apply policies from `src/apim/policies/`

## 3) Daily dev workflow

```powershell
# Terminal 1: Start Docker containers
docker compose up --build

# Terminal 2: Start DevTunnel (after containers are healthy)
.\scripts\devtunnel-start.ps1

# Terminal 3: Start Angular dev server (optional, for hot reload)
cd src\frontend
ng serve
```

Flow to validate:

`Browser (localhost:4200 or localhost:8080) → APIM → DevTunnel → local Docker agent-host → Docker mcp-wfm → Azure SQL`

## 4) Switching between local and cloud

- **Local dev:** `backend-url` = DevTunnel URL
- **Cloud deploy:** `backend-url` = ACA URL (example: `https://calabriomafpoc-aca.azurecontainerapps.io`)

Update options:

- Azure Portal → APIM → Named values
- Azure CLI:
  - `az apim nv update --named-value-id backend-url --value "https://new-url"`

## 5) Troubleshooting

- DevTunnel not connecting:
  - Confirm login state with `devtunnel user login`
- CORS issues:
  - CORS is handled at APIM, not directly at backend
- 401 errors:
  - Verify MSAL config and APIM JWT validation policies
- Connection refused:
  - Check container health with `docker compose ps`

## 6) Architecture (ASCII)

```text
┌──────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Browser     │────▶│  APIM            │────▶│  DevTunnel      │
│  :4200/:8080 │     │  JWT validation  │     │  *.devtunnels.ms│
└──────────────┘     │  Claim extraction│     └────────┬────────┘
                     │  Rate limiting   │              │
                     └──────────────────┘              ▼
                                              ┌─────────────────┐
                                              │  Docker Desktop  │
                                              │  ┌─────────────┐│
                                              │  │ agent-host  ││
                                              │  │ :8000       ││
                                              │  └──────┬──────┘│
                                              │         │       │
                                              │  ┌──────▼──────┐│
                                              │  │ mcp-wfm     ││
                                              │  │ :8001       ││     ┌───────────┐
                                              │  └──────┬──────┘│────▶│ Azure SQL │
                                              │         │       │     └───────────┘
                                              │  ┌──────▼──────┐│
                                              │  │ frontend    ││
                                              │  │ :8080       ││
                                              │  └─────────────┘│
                                              └─────────────────┘
```
