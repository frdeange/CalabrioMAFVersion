# APIM policies for `calabriomafpoc-apim`

This folder contains versioned API Management policies for Sprint 2 Issue #29.

## Files

- `policies/chat-api.xml` → `POST /chat` operation policy (JWT validation, claim headers, per-user rate limit, backend routing)
- `policies/health-api.xml` → `GET /health` and `GET /ready` operation policy (simple proxy routing)

## Azure Portal import steps

1. Open **API Management services** → `calabriomafpoc-apim`.
2. Go to **APIs** and open the API that fronts the Agent Host backend.
3. For operation `POST /chat`:
   - Open **Design** → select operation → **Frontend** → **Policies**.
   - Replace policy XML with `src/apim/policies/chat-api.xml`.
   - Save.
4. For operations `GET /health` and `GET /ready`:
   - Repeat the same process using `src/apim/policies/health-api.xml`.

## Configure Named Value `backend-url`

1. In APIM, open **Named values**.
2. Create or update key `backend-url`.
3. Set value to the current backend base URL (no trailing slash preferred).
4. Ensure policy uses `{{backend-url}}` in `<set-backend-service>`.

## Backend URL switching (DevTunnel vs ACA)

- **Local dev via DevTunnel**  
  Set `backend-url` to your active DevTunnel HTTPS URL (example: `https://<id>.<region>.devtunnels.ms`).
- **Cloud deployment via ACA**  
  Set `backend-url` to your ACA ingress URL (example: `https://<aca-app>.<region>.azurecontainerapps.io`).

Switching environments only requires changing Named Value `backend-url`; no policy XML edits are needed.

## APIM API definition checklist

Configure these operations in the API:

1. `POST /chat` (secured with Entra JWT policy)
2. `GET /health` (no JWT)
3. `GET /ready` (no JWT)

Recommended:
- Add an `OPTIONS` operation for CORS preflight where required by frontend behavior.
- Keep API revisioning enabled for policy rollbacks.

## Security note

- `chat-api.xml` validates Entra ID v2.0 tokens against:
  - OpenID metadata: `https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration`
  - Audience: `api://9dfbf018-d41b-4579-8b6c-e58d1a9a52be`
- HMAC signing for internal headers is intentionally left as TODO pending Key Vault secret wiring.
