# Propuesta de Arquitectura Modernizada — Supervisor Assist
## Microsoft Agent Framework (Python) + Foundry Agent Service + ACA + MCP

> Esta propuesta es la base para una **PoC real**. Todos los flujos, contratos, middleware y observabilidad están detallados al nivel necesario para implementar.

---

## 0. Aclaraciones previas

**Microsoft Agent Framework (MAF)** es el framework GA de Microsoft (open source) para construir agentes en producción. Sucede a Semantic Kernel y AutoGen, y comparte equipo.

- Repo: https://github.com/microsoft/agent-framework
- PyPI: `agent-framework` (y subpaquetes como `agent-framework-foundry`)
- Tiene dos primitivas: **Agents** y **Workflows** (grafos de executors con type safety, checkpointing, HITL, streaming).

**Foundry Agent Service (FAS)** es el servicio gestionado de Azure AI Foundry donde se **crean y persisten** las definiciones de los agentes (instrucciones, tools declarados, modelos asignados, versiones). FAS se integra con MAF a través de la clase `FoundryAgent`, que actúa como cliente local de un agente persistido en Foundry.

**HMAC (Hash-based Message Authentication Code)**: técnica criptográfica que combina una clave secreta con una función hash (SHA-256 típicamente) para generar una "firma" sobre un mensaje. El receptor, conociendo la misma clave, recalcula la firma y la compara: si coincide, sabe que (1) nadie alteró el mensaje y (2) procede de alguien que conocía la clave. En esta arquitectura lo usamos para que el **SQL Builder** firme su plan SQL y el **Query Executor** verifique que el plan no fue manipulado entre agentes.

---

## 1. Arquitectura propuesta (visión general)

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                AZURE CONTAINER APPS ENVIRONMENT (VNET integrada)                  │
│                                                                                    │
│   ┌──────────────┐                                                                │
│   │  Angular UI  │                                                                │
│   │ (Calabrio)   │                                                                │
│   └──────┬───────┘                                                                │
│          │                                                                         │
│          ▼                                                                         │
│   ┌──────────────┐    APIM · AuthN Entra ID · rate limit · policy fragments       │
│   │     APIM     │    Inyecta headers: x-user-oid, x-user-tid, x-user-teams       │
│   └──────┬───────┘                                                                │
│          │                                                                         │
│          ▼                                                                         │
│   ┌──────────────────────────────────────────────────────────────────────┐       │
│   │  ACA: Agent Host (Python + FastAPI + agent-framework)                │       │
│   │                                                                      │       │
│   │  • POST /chat (SSE streaming)                                        │       │
│   │  • WorkflowBuilder secuencial con routing condicional                │       │
│   │  • 3 FoundryAgent clients → agentes en Foundry Agent Service         │       │
│   │  • Middleware Agent/Function (PII, prompt shields, HMAC, SQL pre-val)│       │
│   │  • AgentSession persistido en Cosmos DB                              │       │
│   │  • configure_otel_providers() → OTLP → App Insights                  │       │
│   └─────┬───────────────────┬────────────────────────────┬───────────────┘       │
│         │                   │                            │                         │
│         │ HTTPS              │ MCP Streamable HTTP        │ MCP Streamable HTTP    │
│         ▼                   ▼                            ▼                         │
│   ┌──────────────┐  ┌──────────────────┐    ┌──────────────────────┐             │
│   │  Foundry     │  │ ACA: MCP Server  │    │ ACA: MCP Server      │             │
│   │  Agent       │  │ Schema Provider  │    │ SQL Executor         │             │
│   │  Service     │  │ (Python/FastMCP) │    │ (Python/FastMCP)     │             │
│   │              │  │                  │    │                      │             │
│   │  3 agents:   │  │ Tools:           │    │ Tools:               │             │
│   │  • Intent    │  │ • list_views     │    │ • validate_query     │             │
│   │  • SqlBuilder│  │ • get_schema     │    │ • execute_query      │             │
│   │  • Executor  │  │ • get_joins      │    └────────┬─────────────┘             │
│   │              │  │ • get_rules      │             │                            │
│   │  (versioned, │  │ • sample_queries │             │ Managed Identity           │
│   │   audited)   │  └────────┬─────────┘             │ Private Endpoint           │
│   └─────┬────────┘           │                       ▼                            │
│         │                    ▼            ┌──────────────────────┐                │
│         │            ┌──────────────┐     │  Azure SQL DB        │                │
│         │            │ Blob Storage │     │  (analytics views)   │                │
│         │            │ schemas/*.json│    └──────────────────────┘                │
│         │            └──────────────┘                                              │
│         ▼                                                                          │
│   Azure OpenAI (Private Endpoint) ◄── usado por los agents creados en Foundry     │
└──────────────────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
                  ┌──────────────────────┐
                  │   Azure Monitor /    │
                  │   App Insights       │
                  │   (OTLP receiver)    │
                  └──────────────────────┘
```

**Componentes externos**: Azure OpenAI con Private Endpoint, Azure Key Vault para HMAC keys, Cosmos DB para AgentSession, Azure Content Safety para Prompt Shields.

---

## 2. Decisiones arquitectónicas clave

### 2.1 Por qué 3 agentes especializados (no uno solo)

**Principio de mínimo privilegio**: cada agente ve un conjunto distinto de MCP tools.

| Agente | Tools que puede invocar | Acceso a datos | Capacidad |
|--------|--------------------------|----------------|-----------|
| Intent Classifier | (ninguna) | Ninguno | Clasifica intención, módulo, paginación |
| SQL Builder | Schema Provider MCP (read-only metadata) | Metadatos | Genera SQL; **no la ejecuta** |
| Query Executor | SQL Executor MCP | Lectura sobre vistas whitelisted | Ejecuta SQL pre-firmada; **no la genera** |

- Si el SQL Builder sufre prompt injection, lo peor que puede hacer es leer schemas (no destructivo).
- Si el Query Executor sufre prompt injection, no puede inventar SQL desde cero — solo ejecuta SqlPlans firmados por el SQL Builder.
- **Auditoría granular**: cada salto entre agentes es un punto independiente de logging y enforcement.

### 2.2 Por qué Foundry Agent Service para hostear los agentes

- **Definiciones versionadas** en Foundry (instrucciones, modelo asignado, tools declarados, evaluations).
- **UI de Foundry** permite a no-developers ajustar prompts e iterar.
- **Threads y conversaciones** server-side, visibles en Foundry para auditoría.
- **Evaluaciones built-in** (groundedness, relevance, content safety) sobre los outputs de cada agente.
- **MAF** se queda con la orquestación (workflow, middleware local, structured outputs validadas localmente, integración con MCPs en ACA).

> **División de responsabilidades**: Foundry = definición de agente + modelo + threads. MAF = orquestación + control + observabilidad local.

### 2.3 Por qué un MAF Workflow secuencial con routing condicional

El flujo del partner es determinista: Intent → (si DataQuery) → SqlBuilder → Executor. Esto encaja perfectamente con `WorkflowBuilder` en Python, que ofrece:

- **Edges con condición** (`add_edge(a, b, condition=lambda r: ...)`)
- **Type safety** entre executors (mensajes tipados con Pydantic)
- **Eventos** observables por executor (cada paso emite WorkflowEvent)
- **Streaming** end-to-end (SSE al frontend)
- **Checkpointing** para resumir si falla un paso
- **HITL** opcional con `ctx.request_info()` (aprobación humana de queries críticas)

### 2.4 Hosted MCP vs Local MCP — por qué elegimos Local

Una de las decisiones más importantes y menos obvias de esta arquitectura. Las **tools MCP** pueden conectarse al agente de **dos formas radicalmente distintas**, y eso cambia quién hace la llamada al MCP server, quién la ve y quién puede interceptarla.

#### 2.4.1 Hosted MCP (Foundry hace la llamada)

En esta modalidad, el MCP server se registra en la **definición del agente dentro de Foundry Studio** como "hosted tool". Cuando el LLM decide invocar una tool, **Foundry**, internamente desde su infraestructura, hace la llamada HTTP/SSE al MCP server, recibe el resultado y lo incorpora a la conversación. Tu código (el Agent Host) **nunca ve la tool call**; recibe solo la respuesta final del agente.

```
[Agent Host (MAF)]                          [Foundry Agent Service]
       │                                              │
       │  ──────── message ────────────────────────► │
       │                                              │
       │                                  ┌───────────┘
       │                                  │ "voy a llamar get_schema()"
       │                                  ▼
       │                          [MCP en ACA]   ← Foundry necesita
       │                                  │       acceso a tu MCP
       │                                  ▼          desde fuera de tu VNET
       │                          ◄───────┘
       │                                  │
       │                  ┌───────────────┘
       │                  │ "voy a llamar execute_query()"
       │                  ▼
       │             [MCP en ACA]
       │                  ▼
       │              ────────────┐
       │                          │ formatea respuesta
       │  ◄──── final response ───┘
       │
       ▼
   (resultado final, sin tool calls visibles)
```

**Consecuencias**:
- El **MCP server tiene que ser accesible desde Foundry** (network egress hacia tu VNET — más complejidad de networking).
- MAF no puede interceptar las tool calls → **`FunctionMiddleware` NO se ejecuta**.
- Solo `AgentMiddleware` a nivel de run (entrada/salida del agente entero) funciona.
- No puedes **propagar `traceparent` ni `x-user-context`** de forma controlada al MCP — depende de lo que Foundry decida reenviar.
- Más simple para casos triviales; **inadecuado** cuando necesitas observabilidad, auditoría o RBAC por usuario.

#### 2.4.2 Local MCP (MAF hace la llamada — nuestra elección)

En esta modalidad, en Foundry Studio el agente solo declara los **nombres y schemas de las tools** (no la URL del MCP). El cliente MCP vive en el **Agent Host** y es MAF quien orquesta el bucle:

1. El Agent Host envía el mensaje al agente en Foundry, incluyendo el catálogo de tools disponibles.
2. El LLM responde con un "tool call" (sin ejecutarlo): "quiero llamar `get_schema(view='vw_Absences')`".
3. **MAF**, en el Agent Host, recibe ese tool call y lo ejecuta llamando al MCP en ACA por HTTP.
4. MAF devuelve el resultado al agente en Foundry; el LLM continúa razonando.
5. Cada iteración del bucle pasa por **AgentMiddleware** y **FunctionMiddleware**.

```
[Agent Host (MAF)]                          [Foundry Agent Service]
       │                                              │
       │  ──────── message + tools schema ─────────► │
       │                                              │
       │  ◄─── tool call: get_schema(...) ────────────│
       │                                              │
       │  ┌─ FunctionMiddleware: pre  ─┐              │
       │  │  • SchemaAccessAudit       │              │
       │  │  • Inject x-user-context   │              │
       │  └─────────────────────────────┘             │
       │                                              │
       │  ──► [MCP Schema en ACA]                     │
       │      (en tu VNET; nunca expuesto al exterior)│
       │  ◄─── result ─                               │
       │                                              │
       │  ┌─ FunctionMiddleware: post ─┐              │
       │  │  • Log duration            │              │
       │  └─────────────────────────────┘             │
       │                                              │
       │  ──────── tool result ─────────────────────► │
       │                                              │
       │  ◄─── tool call: execute_query(...) ─────────│
       │                                              │
       │  (mismo patrón: middleware → MCP SQL → middleware)
       │                                              │
       │  ──────── tool result ─────────────────────► │
       │                                              │
       │  ◄─── final response (texto + structured) ───│
       ▼
```

**Consecuencias**:
- El **MCP server NO necesita ser accesible desde Foundry**. Vive 100% dentro de tu VNET, con ingress interno de ACA — superficie de ataque mínima.
- MAF ve y controla **cada tool call** → `FunctionMiddleware` aplica plenamente.
- Puedes **propagar headers custom** (identidad del usuario, traceparent, correlation id) en cada llamada MCP.
- **Más latencia** (1 hop extra: Foundry → Host → MCP en vez de Foundry → MCP directo), pero típicamente <20 ms intra-VNET.
- Más control = más responsabilidad: tu código debe orquestar bien el bucle (MAF lo hace por ti, pero el comportamiento es asíncrono).

#### 2.4.3 Tabla comparativa

| Aspecto | Hosted MCP | Local MCP (elegida) |
|---------|-----------|----------------------|
| Quién llama al MCP server | Foundry | Agent Host (MAF) |
| MCP server expuesto a | Foundry (red pública o PE) | Solo VNET interna |
| `AgentMiddleware` | ✅ (run-level únicamente) | ✅ Completo |
| `FunctionMiddleware` | ❌ No aplica | ✅ Aplica por tool call |
| Headers custom (`x-user-context`, `traceparent`) | Limitado, depende de Foundry | ✅ Control total |
| Trazas OTel del MCP en tu Application Insights | Solo si Foundry exporta | ✅ Sí, son tuyas |
| RBAC por usuario en el MCP | Difícil | ✅ Trivial |
| Latencia E2E | -1 hop | +1 hop (~20 ms) |
| Complejidad de networking | Más (egress Foundry → MCP) | Menos (todo intra-VNET) |

#### 2.4.4 Cómo se configura cada agente en Foundry para Local MCP

En **Foundry Studio**, la definición de cada agente declara los tools por **nombre + schema JSON**, sin URL. Ejemplo del agente `wfm-sql-builder`:

```yaml
name: wfm-sql-builder
version: 1.0.0
model: gpt-4o
temperature: 0.1
instructions: |
  Eres experto SQL. Usa list_views, get_schema, get_joins, get_rules.
  Devuelve un SqlPlan en JSON estricto.
response_format:
  type: json_schema
  json_schema: { ... }   # SqlPlan
tools:
  - name: list_views
    description: "Lists database views available for the current user"
    parameters: { type: object, properties: {}, required: [] }
  - name: get_schema
    description: "Returns the schema for a specific view"
    parameters:
      type: object
      properties:
        view_name: { type: string }
      required: [view_name]
  - name: get_joins
    description: "..."
    parameters: { ... }
  - name: get_rules
    description: "..."
    parameters: { type: object, properties: {}, required: [] }
  - name: sample_queries
    description: "..."
    parameters: { ... }
```

Y en el Agent Host (Python) **se hace el binding a la URL real**:

```python
schema_mcp = MCPStreamableHTTPTool(
    name="schema-provider",
    url=os.environ["MCP_SCHEMA_URL"],   # http://mcp-schema/mcp (intra-VNET)
    # headers per request: ver sección 2.5
)

sql_builder = FoundryAgent(
    project_endpoint=PROJECT,
    agent_name="wfm-sql-builder",
    agent_version="1.0.0",
    credential=credential,
    tools=schema_mcp,                   # ← MCP local; MAF orquesta
)
```

Cuando el LLM en Foundry emite el tool call `list_views`, MAF lo conecta con la implementación correspondiente en `schema_mcp` (matching por nombre). Foundry no sabe ni necesita saber dónde vive el MCP server real.

> **Verificar en el Sprint 0 (spike)**: confirmar con la versión exacta de `agent-framework-foundry` que esta integración (FoundryAgent + MCPStreamableHTTPTool) funciona como se describe, ya que la API del framework está evolucionando. Ver sección 9.6 "Spike de validación".

---

### 2.5 Propagación de identidad del usuario end-to-end

Para que cada capa pueda hacer enforcement de seguridad (RBAC, audit, row-level security en SQL), la **identidad del usuario** debe viajar de forma fiable desde el browser hasta Azure SQL. Este es el flujo exacto.

#### 2.5.1 Flujo de identidad

```
[Browser]
  │  Authorization: Bearer <JWT firmado por Entra ID>
  ▼
[APIM]
  │  • Valida el JWT (audience, issuer, expiry, signature)
  │  • Extrae claims:  oid, tid, preferred_username, groups
  │  • Resuelve "teams" del supervisor (consulta a Graph o claim custom)
  │  • Strip del Authorization original
  │  • Inserta headers internos:
  │       x-user-oid:    <oid>
  │       x-user-tid:    <tid>
  │       x-user-upn:    <preferred_username>
  │       x-user-teams:  <base64(JSON.stringify([...]))>
  │       x-user-roles:  <base64(JSON.stringify([...]))>
  │  • Firma estos headers con un HMAC compartido APIM↔Agent Host (opcional pero recomendado)
  │       x-user-sig:    <HMAC-SHA256 sobre los headers anteriores>
  ▼
[Agent Host (MAF)]
  │  • Verifica x-user-sig (rechaza si no coincide)
  │  • Construye UserContext (Pydantic) a partir de headers
  │  • Lo guarda en:
  │      - request scope (FastAPI Depends)
  │      - context del workflow (visible para todos los executors)
  │      - shared_state de middleware
  │      - ContextVar global (para el cliente MCP)
  │
  │  Para CADA tool call MCP que MAF orquesta:
  │     httpx event hook lee el ContextVar y añade headers:
  │       x-user-context:   <base64(UserContext.model_dump_json())>
  │       x-correlation-id: <trace_id actual>
  │       traceparent:      <W3C estándar, automático por OTel>
  ▼
[MCP Server (Schema o SQL Exec)]
  │  • Middleware HTTP:
  │     - Lee x-user-context, lo deserializa a UserContext
  │     - Lo guarda en ContextVar de la request
  │     - Valida que la Managed Identity del Agent Host es la esperada
  │       (mutual auth a nivel red: solo el Agent Host puede llamar al MCP)
  │  • Cada @mcp.tool puede leer current_user.get() para:
  │     - RBAC (filtrar vistas según roles)
  │     - Audit log (registrar quién hizo qué)
  │     - Inyección de filtros en SQL (TeamName IN (...) usando user.teams)
  ▼
[Azure SQL]
  • Recibe SQL con el filtro de teams ya inyectado por el MCP
  • Conexión autenticada con la MI del MCP SQL Executor (no del usuario)
```

#### 2.5.2 Por qué hacemos "delegación" (no impersonation completa)

Hay dos formas de propagar identidad:

| Patrón | Descripción | Por qué no |
|--------|-------------|------------|
| **Impersonation completa** | Cada servicio se autentica como el usuario (OBO flow, tokens delegados hasta SQL) | Complejo, requiere que Azure SQL acepte tokens AAD por usuario, latencia añadida, y muchas Manage Identities |
| **Delegación con header** ✅ | Servicios se autentican entre sí con MI; la identidad del usuario viaja como "contexto" en headers firmados | Simple, performante, suficiente para enforcement intra-VNET, ampliamente usado |

La delegación funciona porque el perímetro de confianza es **toda la VNET de ACA**: solo el Agent Host puede llamar al MCP (ingress interno), solo el MCP puede llamar a SQL (PE + MI). Dentro de ese perímetro, los headers son fiables si están firmados.

#### 2.5.3 Implementación de la inyección de headers en MCP local

El reto técnico: cuando MAF hace una tool call MCP, ¿cómo añadimos headers HTTP dinámicamente por request (porque `user_ctx` cambia)?

**Approach recomendado**: usar `ContextVar` + un event hook de `httpx` en el cliente MCP.

```python
# mcp_client_context.py
from contextvars import ContextVar
from models import UserContext
import base64, json, httpx

current_user_ctx: ContextVar[UserContext | None] = ContextVar("user_ctx", default=None)

async def inject_user_context_header(request: httpx.Request):
    """httpx event hook — se llama antes de cada request HTTP saliente."""
    user = current_user_ctx.get()
    if user:
        blob = base64.b64encode(user.model_dump_json().encode()).decode()
        request.headers["x-user-context"] = blob

def build_mcp_tools():
    """Construye los clientes MCP una sola vez al arranque, reutilizables."""
    schema_client = httpx.AsyncClient(
        event_hooks={"request": [inject_user_context_header]},
        timeout=30,
    )
    sqlexec_client = httpx.AsyncClient(
        event_hooks={"request": [inject_user_context_header]},
        timeout=60,
    )

    schema_mcp = MCPStreamableHTTPTool(
        name="schema-provider",
        url=os.environ["MCP_SCHEMA_URL"],
        http_client=schema_client,     # ← cliente con hook (verificar nombre del parámetro)
    )
    sqlexec_mcp = MCPStreamableHTTPTool(
        name="sql-executor",
        url=os.environ["MCP_SQLEXEC_URL"],
        http_client=sqlexec_client,
    )
    return schema_mcp, sqlexec_mcp
```

Y en el endpoint FastAPI:

```python
@app.post("/chat")
async def chat(req: Request, ...):
    user_ctx = parse_user_context_from_headers(req.headers)
    token = current_user_ctx.set(user_ctx)   # ← cualquier MCP call de este request llevará el header
    try:
        # ... ejecutar workflow ...
    finally:
        current_user_ctx.reset(token)
```

> **A verificar en Sprint 0**: el nombre exacto del parámetro `http_client` (o equivalente) en `MCPStreamableHTTPTool` puede variar. Plan B si no se puede inyectar httpx custom: subclasear `MCPStreamableHTTPTool` y sobreescribir el método que construye la request.

#### 2.5.4 Lectura del contexto en el MCP server (FastMCP)

```python
# schema_mcp/server.py
from contextvars import ContextVar
from mcp.server.fastmcp import FastMCP
import base64, json

mcp = FastMCP("schema-provider")
current_user: ContextVar[dict | None] = ContextVar("current_user", default=None)

@mcp.middleware
async def extract_user_context(request, call_next):
    blob = request.headers.get("x-user-context")
    if blob:
        user = json.loads(base64.b64decode(blob))
        token = current_user.set(user)
        try:
            return await call_next(request)
        finally:
            current_user.reset(token)
    else:
        # Política: rechazar si no hay contexto de usuario
        return Response(status_code=401, body={"error": "missing user context"})

@mcp.tool(description="...")
async def get_schema(view_name: str) -> ViewSchema:
    user = current_user.get()
    if not user:
        raise PermissionError("no user context")
    if not _authz.user_can_read_view(user, view_name):
        raise PermissionError(f"User {user['oid']} cannot read {view_name}")
    return await _repo.get_schema(view_name)
```

#### 2.5.5 Defensa contra spoofing del header

Aunque la VNET ya aísla el tráfico, añadimos defensa adicional:

1. **MCP Server requiere mTLS o autenticación AAD** del Agent Host. La Managed Identity del Agent Host debe estar autorizada en el MCP (validar el `Authorization: Bearer <MI token>` en la middleware del MCP).
2. **HMAC sobre `x-user-context`**: el Agent Host firma el header con una clave en Key Vault que también conoce el MCP. Si alguien con acceso a la red intentara llamar al MCP con un `x-user-context` falsificado, no podría firmarlo correctamente.

```python
# En el Agent Host, antes de hacer la request:
import hmac, hashlib
sig = hmac.new(SHARED_KEY, blob.encode(), hashlib.sha256).hexdigest()
request.headers["x-user-context"] = blob
request.headers["x-user-context-sig"] = sig

# En el MCP server middleware:
expected = hmac.new(SHARED_KEY, blob.encode(), hashlib.sha256).hexdigest()
if not hmac.compare_digest(expected, request.headers.get("x-user-context-sig", "")):
    return Response(401, {"error": "invalid user context signature"})
```

> Esta es la **misma técnica HMAC** que usamos para el SqlPlan entre SQL Builder y Query Executor (sección 5.2). Reutilizamos el mecanismo, distintas claves.

---

## 3. Defense in Depth — 4 capas de control

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Capa 1 · APIM (perímetro)                                                    │
│   AuthN Entra ID · rate limiting · políticas por tenant · WAF                │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Capa 2 · MAF Middleware (Agent Host, en proceso)                             │
│   Preventivo: PII redaction · Prompt Shields · structured-output validation  │
│   · token budget · SQL pre-validation · HMAC sign/verify · audit             │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Capa 3 · MCP server scope (segregación de privilegios)                       │
│   Schema MCP: solo metadatos, RBAC por vista                                 │
│   SQL Exec MCP: solo SELECT, vistas whitelisted, MI propia con permisos     │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Capa 4 · SQL Guardrails (dentro del MCP SQL Executor — última línea)         │
│   Parse · SELECT-only · whitelist · no system tables · complexity limits ·  │
│   WHERE TeamName IN (...) inyectado · timeout · row limit                    │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                          Azure SQL DB (Private Endpoint)
```

La **Capa 2** es nueva respecto al diseño actual del partner; **complementa** (no sustituye) los guardrails de Capa 4.

---

## 4. Componentes en detalle

### 4.1 Frontend Angular

Sin cambios funcionales. Único cambio recomendado: consumir el endpoint `/chat` con **SSE** para recibir eventos del Workflow en tiempo real (Intent detectado → SQL generada → Ejecutando → Resultado) en lugar de un spinner ciego.

### 4.2 APIM

- AuthN Entra ID con JWT validation policy.
- Inyecta como headers internos: `x-user-oid`, `x-user-tid`, `x-user-teams` (JSON-array codificado en base64).
- Rate limit por usuario y por tenant.
- Single entry point a la VNET; ACA con ingress interno.
- Política `set-header` para añadir el `traceparent` si el cliente no lo envía.

### 4.3 Agent Host (Python + FastAPI + agent-framework)

#### 4.3.1 Stack

```
Python 3.12
agent-framework (>= 1.0)
agent-framework-foundry
azure-identity
fastapi
uvicorn
opentelemetry-sdk
opentelemetry-exporter-otlp
azure-monitor-opentelemetry
pydantic >= 2
mcp (cliente MCP)
```

#### 4.3.2 Definición de los modelos de mensaje (Pydantic)

```python
# models.py
from enum import Enum
from typing import Annotated, Literal
from pydantic import BaseModel, Field

class IntentType(str, Enum):
    DATA_QUERY = "DataQuery"
    SMALL_TALK = "SmallTalk"
    OUT_OF_SCOPE = "OutOfScope"

class UserContext(BaseModel):
    oid: str                       # Azure AD object id
    tid: str                       # tenant id
    teams: list[str]               # team names the supervisor manages
    roles: list[str] = []

class IntentResult(BaseModel):
    type: IntentType
    module: str | None = None
    needs_pagination: bool = False
    confidence: float = Field(ge=0.0, le=1.0)

class SqlPlan(BaseModel):
    sql: str
    views: list[str]
    estimated_rows: int = 0
    rationale: str
    hmac: str = ""                 # firmado por el SQL Builder middleware

class TableRow(BaseModel):
    cells: dict[str, str | int | float | None]

class QueryMetadata(BaseModel):
    rows_returned: int
    duration_ms: int
    views_used: list[str]

class QueryOutput(BaseModel):
    answer: str
    table: list[TableRow] | None = None
    metadata: QueryMetadata
```

#### 4.3.3 Construcción de los 3 FoundryAgent

Asumimos que los agentes ya están definidos en **Foundry Studio** con sus instrucciones, modelo asignado y tools declarados. El código local los referencia por `agent_name` + `agent_version`:

```python
# agents_factory.py
import os
from agent_framework import Agent, MCPStreamableHTTPTool
from agent_framework.foundry import FoundryAgent
from azure.identity.aio import DefaultAzureCredential

PROJECT = os.environ["FOUNDRY_PROJECT_ENDPOINT"]

def make_intent_agent(credential) -> FoundryAgent:
    return FoundryAgent(
        project_endpoint=PROJECT,
        agent_name="wfm-intent-classifier",
        agent_version="1.0.0",
        credential=credential,
        # No tools: este agente solo clasifica
    )

def make_sql_builder_agent(credential, schema_mcp: MCPStreamableHTTPTool) -> FoundryAgent:
    return FoundryAgent(
        project_endpoint=PROJECT,
        agent_name="wfm-sql-builder",
        agent_version="1.0.0",
        credential=credential,
        tools=schema_mcp,           # MCP local; MAF orquesta las tool calls
    )

def make_query_executor_agent(credential, sql_mcp: MCPStreamableHTTPTool) -> FoundryAgent:
    return FoundryAgent(
        project_endpoint=PROJECT,
        agent_name="wfm-query-executor",
        agent_version="1.0.0",
        credential=credential,
        tools=sql_mcp,
    )
```

#### 4.3.4 Ensamblaje del Workflow

```python
# workflow_factory.py
from agent_framework import WorkflowBuilder, executor
from models import IntentResult, IntentType, SqlPlan, QueryOutput, UserContext

def build_workflow(intent_agent, sql_builder_agent, executor_agent):
    return (
        WorkflowBuilder(start_executor=intent_agent)
        .add_edge(
            intent_agent,
            sql_builder_agent,
            condition=lambda r: r.structured_output(IntentResult).type == IntentType.DATA_QUERY,
        )
        .add_edge(sql_builder_agent, executor_agent)
        # Si la intención no es DataQuery, el workflow termina tras el Intent
        .build()
    )
```

#### 4.3.5 Endpoint FastAPI con SSE

```python
# main.py
import json, asyncio
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from agent_framework import MCPStreamableHTTPTool
from agent_framework.observability import configure_otel_providers, get_tracer
from azure.identity.aio import DefaultAzureCredential
from opentelemetry.trace import SpanKind

from agents_factory import make_intent_agent, make_sql_builder_agent, make_query_executor_agent
from workflow_factory import build_workflow
from middleware import build_middleware_stack
from models import UserContext

configure_otel_providers(enable_sensitive_data=False)  # PII off en spans
app = FastAPI()

@app.on_event("startup")
async def startup():
    app.state.credential = DefaultAzureCredential()
    app.state.schema_mcp = await MCPStreamableHTTPTool(
        name="schema-provider",
        url="http://mcp-schema/mcp",   # ingress interno ACA
    ).__aenter__()
    app.state.sql_mcp = await MCPStreamableHTTPTool(
        name="sql-executor",
        url="http://mcp-sqlexec/mcp",
    ).__aenter__()

@app.post("/chat")
async def chat(req: Request):
    body = await req.json()
    user_ctx = UserContext(
        oid=req.headers["x-user-oid"],
        tid=req.headers["x-user-tid"],
        teams=json.loads(req.headers["x-user-teams"]),
    )

    # Construir agentes con middleware aplicado
    middleware = build_middleware_stack(user_ctx)
    intent = make_intent_agent(app.state.credential).with_middleware(middleware["intent"])
    sqlb = make_sql_builder_agent(app.state.credential, app.state.schema_mcp).with_middleware(middleware["sqlb"])
    qexec = make_query_executor_agent(app.state.credential, app.state.sql_mcp).with_middleware(middleware["qexec"])

    workflow = build_workflow(intent, sqlb, qexec)

    async def event_stream():
        with get_tracer().start_as_current_span(
            "workflow.run",
            kind=SpanKind.SERVER,
            attributes={
                "workflow.name": "wfm-supervisor-assist",
                "user.oid_hash": _hash(user_ctx.oid),  # nunca el oid en claro
                "user.tid": user_ctx.tid,
            },
        ) as span:
            async for event in workflow.run_stream(body["message"], context={"user": user_ctx}):
                payload = {"type": event.kind, "data": event.to_dict()}
                yield f"data: {json.dumps(payload)}\n\n"
            span.set_attribute("workflow.outcome", "success")

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

> Nota: el método `.with_middleware()` y la firma exacta del `WorkflowBuilder` pueden variar con la versión de MAF. El esqueleto refleja la API estable de los samples del repo oficial (`python/samples/02-agents/middleware/class_based_middleware.py` y `python/samples/03-workflows/_start-here/step2_agents_in_a_workflow.py`).

### 4.4 MCP Server — Schema Provider (Python + FastMCP)

```python
# schema_mcp/server.py
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel
from contextvars import ContextVar
from typing import Annotated
import json

from observability import setup_tracing, get_tracer
setup_tracing(service_name="mcp-schema-provider")

mcp = FastMCP("schema-provider")
current_user: ContextVar[dict] = ContextVar("current_user")

class ViewSchema(BaseModel):
    view_name: str
    description: str
    columns: list[dict]
    sample_queries: list[str]

@mcp.tool(description="Lists database views available for the current user, filtered by RBAC")
async def list_views() -> list[str]:
    with get_tracer().start_as_current_span("schema.list_views") as span:
        user = current_user.get()
        views = await _repo.views_for_roles(user["roles"])
        span.set_attribute("views.count", len(views))
        return views

@mcp.tool(description="Returns the schema for a specific view")
async def get_schema(view_name: Annotated[str, "Whitelisted view name"]) -> ViewSchema:
    with get_tracer().start_as_current_span("schema.get_schema") as span:
        span.set_attribute("view.name", view_name)
        user = current_user.get()
        if not await _authz.user_can_read_view(user, view_name):
            span.set_attribute("authz.result", "denied")
            raise PermissionError(f"User cannot read view {view_name}")
        schema = await _repo.get_schema(view_name)
        span.set_attribute("view.column_count", len(schema.columns))
        return schema

@mcp.tool(description="Returns join rules between two views")
async def get_joins(view_a: str, view_b: str) -> list[dict]: ...

@mcp.tool(description="Returns global SQL generation rules")
async def get_rules() -> dict: ...

@mcp.tool(description="Returns example queries for a view")
async def sample_queries(view_name: str) -> list[str]: ...

# Middleware HTTP que extrae user context de los headers propagados desde Agent Host
@mcp.middleware
async def extract_user_context(request, call_next):
    user_blob = request.headers.get("x-user-context")
    if user_blob:
        current_user.set(json.loads(user_blob))
    return await call_next(request)
```

**Fuente de datos**: los JSONs (`absence.json`, `people.json`, `_joins.json`, `_global_rules.json`) viven en Blob Storage. Carga al arranque + caché en memoria (TTL 15 min) + invalidación por Event Grid si cambian.

### 4.5 MCP Server — SQL Executor (Python + FastMCP)

```python
# sqlexec_mcp/server.py
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel
from typing import Annotated
import sqlglot, time
from azure.identity.aio import DefaultAzureCredential
from azure.identity import ManagedIdentityCredential

from observability import setup_tracing, get_tracer
setup_tracing(service_name="mcp-sql-executor")

mcp = FastMCP("sql-executor")

WHITELIST_VIEWS = {"vw_PersonDetail", "vw_AbsenceRequest", "mv_personal_account", "mv_scheduling"}
FORBIDDEN_KEYWORDS = {"INSERT","UPDATE","DELETE","DROP","TRUNCATE","EXEC","MERGE","ALTER"}

class QueryResult(BaseModel):
    rows: list[dict]
    row_count: int
    duration_ms: int

@mcp.tool(description="Validates a SQL query without executing it")
async def validate_query(sql: str) -> dict:
    with get_tracer().start_as_current_span("sql.validate") as span:
        result = _validate(sql)
        span.set_attribute("sql.valid", result["valid"])
        return result

@mcp.tool(description="Validates and executes a SQL query against the analytics database")
async def execute_query(
    sql: Annotated[str, "SELECT query against whitelisted views only"],
    user_teams: Annotated[list[str], "Teams the supervisor manages"],
) -> QueryResult:
    tracer = get_tracer()
    with tracer.start_as_current_span("sql.execute_query") as parent:
        parent.set_attribute("sql.length", len(sql))
        parent.set_attribute("user.teams_count", len(user_teams))

        # Layer 4: Guardrails (parse, validar tipo, whitelist, inyección team filter)
        with tracer.start_as_current_span("sql.guardrails") as gspan:
            ast = sqlglot.parse_one(sql, read="tsql")
            if ast.find(sqlglot.exp.Insert) or any(kw in sql.upper() for kw in FORBIDDEN_KEYWORDS):
                gspan.set_attribute("guardrail.result", "rejected_non_select")
                raise ValueError("Only SELECT queries allowed.")
            referenced = {t.name for t in ast.find_all(sqlglot.exp.Table)}
            if not referenced.issubset(WHITELIST_VIEWS):
                gspan.set_attribute("guardrail.result", "rejected_view_not_whitelisted")
                raise ValueError(f"Tables not allowed: {referenced - WHITELIST_VIEWS}")
            hardened_sql = _inject_team_filter(ast, user_teams)
            gspan.set_attribute("guardrail.result", "passed")
            gspan.set_attribute("sql.referenced_views", list(referenced))

        # Layer execute
        with tracer.start_as_current_span("sql.db_query") as dbspan:
            start = time.perf_counter()
            rows = await _pool.fetch(hardened_sql, timeout=30, limit=1000)
            duration_ms = int((time.perf_counter() - start) * 1000)
            dbspan.set_attribute("db.rows_returned", len(rows))
            dbspan.set_attribute("db.duration_ms", duration_ms)

        return QueryResult(rows=rows, row_count=len(rows), duration_ms=duration_ms)
```

**Conexión a Azure SQL**: `aioodbc` con Managed Identity (token AAD) — sin password en código. Pool de conexiones reutilizado.

### 4.6 Foundry Agent Service — definición de los 3 agentes

Cada agente se crea en **Foundry Studio** (o vía API) con esta definición:

| Campo | Intent Classifier | SQL Builder | Query Executor |
|-------|-------------------|-------------|----------------|
| name | wfm-intent-classifier | wfm-sql-builder | wfm-query-executor |
| version | 1.0.0 | 1.0.0 | 1.0.0 |
| model | gpt-4o-mini | gpt-4o | gpt-4o-mini |
| temperature | 0.0 | 0.1 | 0.2 |
| response_format | json_schema (IntentResult) | json_schema (SqlPlan) | json_schema (QueryOutput) |
| instructions | "Clasifica la intención del usuario… devuelve IntentResult" | "Eres experto SQL. Usa list_views, get_schema, get_joins, get_rules. Devuelve SqlPlan." | "Recibes SqlPlan validado. Llama execute_query y formatea." |
| tools_declared | (none) | list_views, get_schema, get_joins, get_rules, sample_queries | validate_query, execute_query |

Los **schemas JSON** correspondientes a los Pydantic models se cargan en Foundry para `strict response_format`.

---

## 5. MAF Middleware — Capa 2 (Python)

MAF Python expone middleware mediante clases que heredan de `AgentMiddleware` o `FunctionMiddleware`. Se inyectan en cada agente.

### 5.1 Mapeo middleware → agente

| Agente | Middleware | Tipo | Propósito |
|--------|-----------|------|-----------|
| Intent | `PromptShieldsMiddleware` | Agent | Detectar prompt injection (Azure Content Safety) |
| Intent | `PiiRedactionInLogsMiddleware` | Agent | Sanear logs de telemetría |
| Intent | `IntentShortCircuitMiddleware` | Agent | Si `OutOfScope`, abortar el workflow |
| SQL Builder | `TokenBudgetMiddleware` | Agent | Cancelar si excede N tokens |
| SQL Builder | `SchemaAccessAuditMiddleware` | Function | Audit log de cada `get_schema()` |
| SQL Builder | `SqlSyntacticPreValidatorMiddleware` | Agent | Rechazar SQL con keywords prohibidas antes de seguir |
| SQL Builder | `HmacSignMiddleware` | Agent | Firma el `SqlPlan` en su salida |
| Query Executor | `HmacVerifyMiddleware` | Agent | Verifica HMAC del `SqlPlan` recibido |
| Query Executor | `ResultPiiRedactionMiddleware` | Agent | Redacta DNI/email en resultados antes de devolver al usuario |
| Query Executor | `AuditLogMiddleware` | Function | Log estructurado de `execute_query` |

### 5.2 Implementaciones de referencia

**Prompt Shields (anti-jailbreak)**

```python
from agent_framework import AgentMiddleware, AgentContext, AgentResponse, Message
from azure.ai.contentsafety.aio import ContentSafetyClient

class PromptShieldsMiddleware(AgentMiddleware):
    def __init__(self, safety_client: ContentSafetyClient):
        self.safety = safety_client

    async def process(self, context: AgentContext, call_next):
        last_user_msg = next((m.text for m in reversed(context.messages) if m.role == "user"), None)
        if not last_user_msg:
            return await call_next()

        result = await self.safety.detect_prompt_injection({"user_prompt": last_user_msg})
        if result.attack_detected:
            context.tracer.add_event("guardrail.prompt_shields", {"attack": True})
            context.result = AgentResponse(
                messages=[Message("assistant", "Petición rechazada por políticas de seguridad.")]
            )
            return  # no llamamos call_next → corta el pipeline
        context.tracer.add_event("guardrail.prompt_shields", {"attack": False})
        await call_next()
```

**HMAC firma + verificación del SqlPlan**

```python
import hmac, hashlib, json
from agent_framework import AgentMiddleware, AgentContext
from models import SqlPlan

class HmacSignMiddleware(AgentMiddleware):
    def __init__(self, secret_key: bytes):
        self.key = secret_key

    async def process(self, context: AgentContext, call_next):
        await call_next()
        if context.result is None: return
        plan = context.result.structured_output(SqlPlan)
        payload = f"{plan.sql}|{sorted(plan.views)}|{plan.estimated_rows}".encode()
        plan.hmac = hmac.new(self.key, payload, hashlib.sha256).hexdigest()
        context.result.set_structured_output(plan)

class HmacVerifyMiddleware(AgentMiddleware):
    def __init__(self, secret_key: bytes):
        self.key = secret_key

    async def process(self, context: AgentContext, call_next):
        plan = SqlPlan.model_validate(context.input.structured_input)
        expected = hmac.new(
            self.key,
            f"{plan.sql}|{sorted(plan.views)}|{plan.estimated_rows}".encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, plan.hmac):
            context.tracer.add_event("guardrail.hmac", {"verified": False})
            raise PermissionError("SqlPlan HMAC mismatch — possible tampering.")
        context.tracer.add_event("guardrail.hmac", {"verified": True})
        await call_next()
```

> **De dónde sale la `secret_key`**: la generamos en Key Vault al desplegar. Tanto el SQL Builder (sign) como el Query Executor (verify) acceden con su Managed Identity. Es la misma clave compartida entre ambos middleware **dentro del mismo Agent Host** (mismo proceso). El HMAC protege contra alteraciones del payload en memoria, logs, o si algún día se introdujera un broker entre executors.

**SQL Pre-Validator (corta antes de gastar el call al Executor)**

```python
import re
from agent_framework import AgentMiddleware, AgentContext, AgentResponse, Message
from models import SqlPlan

FORBIDDEN = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE|EXEC|MERGE|ALTER)\b", re.I)

class SqlSyntacticPreValidatorMiddleware(AgentMiddleware):
    async def process(self, context: AgentContext, call_next):
        await call_next()
        if context.result is None: return
        plan = context.result.structured_output(SqlPlan)
        if FORBIDDEN.search(plan.sql):
            context.tracer.add_event("guardrail.sql_syntactic", {"result": "rejected"})
            context.result = AgentResponse(
                messages=[Message("assistant", "La SQL generada contiene operaciones no permitidas.")]
            )
            return
        context.tracer.add_event("guardrail.sql_syntactic", {"result": "passed"})
```

**Audit log estructurado**

```python
import logging, json, hashlib
from agent_framework import FunctionMiddleware, FunctionInvocationContext

logger = logging.getLogger("audit")

class AuditLogMiddleware(FunctionMiddleware):
    async def process(self, context: FunctionInvocationContext, call_next):
        await call_next()
        if context.function.name == "execute_query":
            sql = context.arguments.get("sql", "")
            query_hash = hashlib.sha256(sql.encode()).hexdigest()[:16]
            logger.info("audit.sql_executed", extra={
                "user_oid_hash": _hash(context.shared_state["user"].oid),
                "query_hash": query_hash,
                "views": context.shared_state.get("views_used", []),
                "rows_returned": context.result.row_count if context.result else None,
                "duration_ms": context.result.duration_ms if context.result else None,
            })
```

---

## 6. Structured Outputs — intercambio tipado entre agentes

### 6.1 Cómo Foundry + MAF lo garantizan

1. En **Foundry**, cada agente tiene `response_format = json_schema(...)` con el schema derivado de los modelos Pydantic. Azure OpenAI fuerza el JSON estricto.
2. En **MAF**, cada `FoundryAgent` puede declarar el `output_model` para que `AgentResponse.structured_output(Model)` deserialice y valide.
3. En el **Workflow**, los edges pueden referenciar los tipos para que la condición lambda reciba un objeto tipado.

### 6.2 Generación del schema JSON desde Pydantic

```python
from models import IntentResult, SqlPlan, QueryOutput
import json

# Esto es lo que subimos a Foundry Studio como response_format del agente
intent_schema = IntentResult.model_json_schema()
sql_plan_schema = SqlPlan.model_json_schema()
query_output_schema = QueryOutput.model_json_schema()
```

Foundry permite registrar este schema en la definición del agente.

### 6.3 Comparativa con el approach actual del partner

| Aspecto | Partner hoy | Propuesta |
|---------|-------------|-----------|
| JSON entre agentes | Manual, validación defensiva | Pydantic + json_schema strict en Azure OpenAI |
| Errores de shape | En runtime | Capturados por el LLM-side |
| Versionado de schema | Manual en prompts | Versionado en Foundry junto al agente |
| Trazabilidad de tipos | Logs | Spans OTel con el tipo en cada paso |

---

## 7. Flujo End-to-End paso a paso

Caso: usuario pregunta *"¿Cuántas ausencias hay esta semana en mi equipo?"*

```
[Browser]
  └─ Genera traceparent: 00-aabbcc...-001-01
  └─ POST /api/chat   { "message": "¿Cuántas ausencias hay esta semana en mi equipo?" }
     Headers: Authorization: Bearer <jwt>, traceparent: 00-aabbcc...-001-01

[APIM]    Span: HTTP POST /api/chat (server)
  ├─ Validate JWT → extrae oid, tid, roles, teams
  ├─ Añade headers: x-user-oid, x-user-tid, x-user-teams (base64 JSON)
  ├─ Rate limit check
  └─ Forward → http://agent-host:8080/chat

[ACA: Agent Host]  Span: workflow.run (server, parent del resto)
  ├─ Attributes:
  │     workflow.name = "wfm-supervisor-assist"
  │     user.oid_hash = "sha256:1a2b…"
  │     user.tid = "<tenant>"
  │     message.length = 47
  │
  ├─ Construye middleware stack para esta request (con user_ctx)
  ├─ Construye agentes (3 FoundryAgent) + workflow (sequential builder)
  │
  ├─►  Span: executor.run name="IntentClassifier"
  │     │
  │     ├─ Span: middleware.PromptShields
  │     │     └─ Llama Content Safety → AttackDetected=false
  │     │
  │     ├─ Span: foundry.agent.invoke name="wfm-intent-classifier" version="1.0.0"
  │     │     ├─ Span: llm.chat (Azure OpenAI)
  │     │     │     attributes: model=gpt-4o-mini, input.tokens=180, output.tokens=42
  │     │     └─ Resultado: { "type": "DataQuery", "module": "Absences", "needs_pagination": false, "confidence": 0.94 }
  │     │
  │     ├─ Span: middleware.JsonShapeValidation
  │     │     └─ Pydantic OK
  │     │
  │     └─ Output: IntentResult
  │
  ├─►  Span: edge.evaluate from=Intent to=SqlBuilder
  │     condition.result = true (DataQuery)
  │
  ├─►  Span: executor.run name="SqlBuilder"
  │     │
  │     ├─ Span: middleware.TokenBudget (current=180 + 1200 schema = OK)
  │     │
  │     ├─ Span: foundry.agent.invoke name="wfm-sql-builder"
  │     │     ├─ Span: llm.chat   (model=gpt-4o, tool_calls=[list_views])
  │     │     │
  │     │     ├─►  Span: mcp.tool.invoke name="list_views"
  │     │     │     ├─ HTTP Span: POST http://mcp-schema/mcp
  │     │     │     │     │
  │     │     │     │     └─ [MCP Schema] Span: schema.list_views (server)
  │     │     │     │           ├─ extract_user_context middleware
  │     │     │     │           ├─ repo.views_for_roles → ["vw_PersonDetail","vw_AbsenceRequest", ...]
  │     │     │     │           └─ views.count = 4
  │     │     │     └─ duration_ms=12
  │     │     │
  │     │     ├─ Span: llm.chat   (con result, decide get_schema)
  │     │     │
  │     │     ├─►  Span: mcp.tool.invoke name="get_schema" view="vw_AbsenceRequest"
  │     │     │     ├─ HTTP Span: POST http://mcp-schema/mcp
  │     │     │     │     └─ [MCP Schema] Span: schema.get_schema view.name="vw_AbsenceRequest"
  │     │     │     │           ├─ authz check → allowed
  │     │     │     │           └─ column_count=12
  │     │     │
  │     │     └─ Span: llm.chat   (final, devuelve SqlPlan JSON)
  │     │           tool_calls=[]   output.tokens=110
  │     │
  │     ├─ Span: middleware.SqlSyntacticPreValidator → passed
  │     ├─ Span: middleware.HmacSign → adds hmac field
  │     │
  │     └─ Output: SqlPlan { sql, views=["vw_AbsenceRequest"], estimated_rows=15, hmac="..." }
  │
  ├─►  Span: executor.run name="QueryExecutor"
  │     │
  │     ├─ Span: middleware.HmacVerify → verified=true
  │     │
  │     ├─ Span: foundry.agent.invoke name="wfm-query-executor"
  │     │     ├─ Span: llm.chat   (decide execute_query)
  │     │     │
  │     │     ├─►  Span: mcp.tool.invoke name="execute_query"
  │     │     │     ├─ HTTP Span: POST http://mcp-sqlexec/mcp
  │     │     │     │     │
  │     │     │     │     └─ [MCP SQL Exec] Span: sql.execute_query
  │     │     │     │           ├─ Span: sql.guardrails
  │     │     │     │           │     guardrail.result = "passed"
  │     │     │     │           │     sql.referenced_views = ["vw_AbsenceRequest"]
  │     │     │     │           │     team filter injected: WHERE TeamName IN ('TeamA','TeamB')
  │     │     │     │           │
  │     │     │     │           └─ Span: sql.db_query
  │     │     │     │                 ├─ Span: db.connect (pool reuse)
  │     │     │     │                 └─ Span: db.query
  │     │     │     │                       db.system="mssql"
  │     │     │     │                       db.rows_returned=8
  │     │     │     │                       db.duration_ms=87
  │     │     │     │
  │     │     │     └─ duration_ms=120
  │     │     │
  │     │     └─ Span: llm.chat   (formatea respuesta natural)
  │     │
  │     ├─ Span: middleware.ResultPiiRedaction → 0 fields redacted
  │     ├─ Span: middleware.AuditLog → emit event "audit.sql_executed"
  │     │
  │     └─ Output: QueryOutput { answer, table[8 rows], metadata }
  │
  ├─ Stream events SSE → Browser
  │     event: ExecutorStarted name=IntentClassifier
  │     event: ExecutorCompleted name=IntentClassifier
  │     event: ExecutorStarted name=SqlBuilder
  │     event: ExecutorToolCalled name=list_views
  │     event: ExecutorToolCalled name=get_schema
  │     event: ExecutorCompleted name=SqlBuilder
  │     event: ExecutorStarted name=QueryExecutor
  │     event: ExecutorToolCalled name=execute_query
  │     event: ExecutorCompleted name=QueryExecutor
  │     event: WorkflowCompleted output=QueryOutput
  │
  └─ Span complete. workflow.outcome="success", total_tokens=940, total_duration_ms=2840

[Browser]  Render progresivo del SSE
```

**Total típico** end-to-end: 2.5–3.5s. Spans generados: ~30, todos correlacionados por `traceparent` W3C.

---

## 8. Observabilidad — el corazón operativo

Todo el sistema usa **OpenTelemetry**. MAF Python lo expone con `configure_otel_providers()` que activa tracing, logging y métricas automáticamente.

### 8.1 Setup en cada servicio

```python
# observability.py (compartido entre Agent Host y MCPs)
import os, logging
from azure.monitor.opentelemetry import configure_azure_monitor
from agent_framework.observability import configure_otel_providers

def setup_tracing(service_name: str):
    # 1. Azure Monitor (envía a App Insights / Log Analytics)
    configure_azure_monitor(
        connection_string=os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"],
        resource_attributes={
            "service.name": service_name,
            "service.namespace": "wfm-supervisor-assist",
            "service.version": os.environ.get("APP_VERSION", "dev"),
            "deployment.environment": os.environ.get("ENVIRONMENT", "dev"),
        },
    )
    # 2. MAF observability (auto-instrumentation de agents, workflows, tool calls, LLM calls)
    configure_otel_providers(enable_sensitive_data=False)

def get_tracer():
    from opentelemetry.trace import get_tracer as ot
    return ot("wfm-supervisor-assist")
```

### 8.2 Atributos custom añadidos en spans

| Capa | Span | Atributos clave |
|------|------|-----------------|
| Workflow | `workflow.run` | `workflow.name`, `user.oid_hash`, `user.tid`, `message.length`, `workflow.outcome`, `total_tokens`, `total_duration_ms` |
| Executor | `executor.run` | `executor.name`, `executor.type`, `agent.name`, `agent.version` |
| Middleware | `middleware.<name>` | `middleware.result` (passed/rejected), atributos específicos |
| LLM | `llm.chat` (auto) | `llm.model`, `llm.input_tokens`, `llm.output_tokens`, `llm.cost_estimate_cents` |
| MCP tool call | `mcp.tool.invoke` | `tool.name`, `tool.duration_ms`, `tool.result_size_bytes` |
| MCP schema server | `schema.*` | `view.name`, `view.column_count`, `authz.result` |
| MCP SQL exec | `sql.guardrails` | `guardrail.result`, `sql.referenced_views`, `team_filter.applied` |
| MCP SQL exec | `sql.db_query` | `db.system`, `db.rows_returned`, `db.duration_ms` |

**Privacidad**: nunca se loguean datos personales en claro (DNI, email, nombres). El `oid` se hashea con SHA-256 antes de adjuntarse como atributo.

### 8.3 Logs estructurados (además de traces)

Eventos críticos emitidos como structured logs en Azure Monitor:

| Evento | Campos | Propósito |
|--------|--------|-----------|
| `audit.sql_executed` | user_oid_hash, query_hash, views, rows_returned, duration_ms, status | Auditoría regulatoria |
| `guardrail.violation` | guardrail_name, reason, user_oid_hash, prompt_excerpt_hash | SecOps |
| `agent.refusal` | agent_name, reason, user_oid_hash | UX/QA |
| `workflow.failed` | workflow_name, executor_failed, error_class | SRE alerting |
| `token.budget_exceeded` | agent_name, tokens, budget | FinOps |

### 8.4 Métricas

| Métrica | Tipo | Uso |
|---------|------|-----|
| `wfm.workflow.duration_ms` | histogram | P50/P95/P99 de latencia E2E |
| `wfm.workflow.outcome` | counter (success/failure/refusal) | Dashboard de salud |
| `wfm.llm.tokens` | counter (input/output, model) | FinOps |
| `wfm.mcp.tool_calls` | counter (tool_name, status) | Detectar tools nunca usadas |
| `wfm.sql.rows_returned` | histogram | Detectar queries que devuelven demasiado |
| `wfm.guardrail.rejections` | counter (guardrail_name) | SecOps |

### 8.5 Dashboards y alertas en App Insights

**Dashboards recomendados**:

1. **Health** — workflow.outcome ratio, P95 latency, error rate por servicio.
2. **FinOps** — tokens consumidos por usuario/tenant/día, coste estimado, top queries por coste.
3. **Security** — guardrail rejections, prompt shields detections, audit log de SQL executed.
4. **Performance** — desglose de latencia por capa (intent vs sql_builder vs executor vs db).

**Alertas críticas**:
- `workflow.failed` rate > 2% en 5 min → PagerDuty.
- `guardrail.violation` > 10 en 1 min → SecOps.
- `db.duration_ms` P95 > 5000 ms → DBA.
- `llm.input_tokens` por request > 8000 → revisar (degradación del MCP Schema Provider).

### 8.6 Trace context propagation

- W3C `traceparent` se propaga automáticamente: Browser → APIM → Agent Host → MCPs → Azure SQL.
- MAF y FastMCP usan OTel SDK que respeta `traceparent` en headers HTTP.
- En Azure Monitor → "Transaction search" muestra el árbol completo por `operation_Id`.

---

## 9. Requisitos para la PoC

### 9.1 Recursos Azure mínimos

| Recurso | Configuración mínima |
|---------|---------------------|
| Resource Group | `rg-wfm-assist-poc` |
| VNET + Subnets | Subnet `aca-env` (/23), subnet `pe` (/27) |
| ACA Environment | Workload profile, ingress interno, VNET integrada |
| ACA × 3 | Agent Host (1 vCPU/2 GB, min=1, max=10), MCP Schema (0.5/1, min=0, max=5), MCP SQL Exec (1/2, min=1, max=10) |
| Azure OpenAI | PE habilitado; gpt-4o + gpt-4o-mini deployments |
| Foundry Project | Conectado al recurso Azure OpenAI |
| APIM | Tier Developer (PoC) o Standard v2 (prod) con VNET |
| Azure SQL DB | PE habilitado, MI granted role db_datareader sobre schema SAChatbot |
| Cosmos DB | Containers: `agent-sessions` (TTL configurable), `audit-events` |
| Blob Storage | Container `schemas` (private, MI access) |
| Key Vault | Secret `hmac-sqlplan-key` (256-bit, rotación 90 días) |
| App Insights | Workspace-based, conectado a Log Analytics |
| Content Safety | Recurso para Prompt Shields |

### 9.2 Identidades

Cada ACA con su propia User-Assigned Managed Identity:

- `mi-agent-host` → Foundry RBAC (Reader+Invoker), Cosmos (DataContributor), Key Vault (Secret User), App Insights, Content Safety (User), Azure OpenAI (User).
- `mi-mcp-schema` → Blob Reader, App Insights.
- `mi-mcp-sqlexec` → SQL DB (db_datareader via AAD group), Key Vault (Secret User), App Insights.

### 9.3 Paquetes Python

```toml
# pyproject.toml (Agent Host)
[project]
dependencies = [
  "agent-framework>=1.0",
  "agent-framework-foundry>=1.0",
  "azure-identity>=1.17",
  "azure-monitor-opentelemetry>=1.6",
  "azure-ai-contentsafety>=1.0",
  "fastapi>=0.115",
  "uvicorn[standard]>=0.32",
  "pydantic>=2.9",
  "mcp>=1.0",
]

# pyproject.toml (MCP servers)
[project]
dependencies = [
  "mcp>=1.0",
  "fastmcp>=2.0",
  "aioodbc>=0.5",
  "sqlglot>=25.0",
  "azure-identity>=1.17",
  "azure-monitor-opentelemetry>=1.6",
  "pydantic>=2.9",
]
```

### 9.4 Variables de entorno por servicio

**Agent Host**
```
FOUNDRY_PROJECT_ENDPOINT=https://<foundry>.services.ai.azure.com/api/projects/<proj>
APPLICATIONINSIGHTS_CONNECTION_STRING=<conn>
COSMOS_ENDPOINT=https://<cosmos>.documents.azure.com:443/
KEYVAULT_URI=https://<kv>.vault.azure.net/
CONTENT_SAFETY_ENDPOINT=https://<cs>.cognitiveservices.azure.com/
MCP_SCHEMA_URL=http://mcp-schema/mcp
MCP_SQLEXEC_URL=http://mcp-sqlexec/mcp
APP_VERSION=1.0.0
ENVIRONMENT=poc
```

**MCP Schema**
```
APPLICATIONINSIGHTS_CONNECTION_STRING=<conn>
SCHEMAS_BLOB_ACCOUNT=<sa>
SCHEMAS_BLOB_CONTAINER=schemas
```

**MCP SQL Executor**
```
APPLICATIONINSIGHTS_CONNECTION_STRING=<conn>
SQL_SERVER=<sqlserver>.database.windows.net
SQL_DATABASE=<db>
KEYVAULT_URI=https://<kv>.vault.azure.net/
HMAC_SECRET_NAME=hmac-sqlplan-key
```

### 9.5 Estructura del repo (monorepo)

```
wfm-supervisor-assist/
├── infra/
│   └── main.bicep             # IaC (azd init compatible)
├── apps/
│   ├── agent-host/
│   │   ├── pyproject.toml
│   │   ├── Dockerfile
│   │   └── src/
│   │       ├── main.py
│   │       ├── agents_factory.py
│   │       ├── workflow_factory.py
│   │       ├── middleware/
│   │       ├── models.py
│   │       └── observability.py
│   ├── mcp-schema/
│   │   └── (similar)
│   └── mcp-sqlexec/
│       └── (similar)
├── foundry/
│   ├── agents/
│   │   ├── wfm-intent-classifier.yaml
│   │   ├── wfm-sql-builder.yaml
│   │   └── wfm-query-executor.yaml
│   └── schemas/               # JSON schemas generados desde Pydantic
└── tests/
    ├── e2e/
    └── unit/
```

### 9.6 Spike de validación — Sprint 0 (CRÍTICO antes de comprometer el diseño)

Antes de construir todas las piezas, dedicamos **5 días laborables a validar las suposiciones técnicas más arriesgadas**. Si alguno de estos spikes revela un bloqueante, ajustamos el diseño antes de avanzar.

| # | Spike | Pregunta a responder | Cómo se valida | Plan B si falla |
|---|-------|----------------------|----------------|-----------------|
| S1 | `FoundryAgent` + `MCPStreamableHTTPTool` (Local MCP) | ¿MAF orquesta correctamente el bucle de tool calls entre Foundry y un MCP local? | Crear un FoundryAgent mínimo con un MCP de "hello world" en ACA, invocar y verificar trazas | Cambiar a `Agent(client=FoundryChatClient(...))` y crear el agente en código (perdemos UI de Foundry pero mantenemos arquitectura) |
| S2 | Middleware `AgentMiddleware` + `FunctionMiddleware` sobre `FoundryAgent` | ¿Ambos tipos de middleware se ejecutan correctamente con FoundryAgent + Local MCP? | Inyectar middleware que logueen y verificar que se ejecutan en cada tool call | Si FunctionMiddleware no aplica, mover los checks a wrappers de executors custom en el Workflow |
| S3 | Headers HTTP custom en `MCPStreamableHTTPTool` | ¿Podemos inyectar `x-user-context` y `x-user-context-sig` por request? | Usar un httpx event hook con ContextVar y verificar headers en el MCP server | Subclasear MCPStreamableHTTPTool o usar el SDK MCP directamente sin el wrapper de MAF |
| S4 | Structured outputs (json_schema strict) en FoundryAgent | ¿El response_format estricto se respeta y `.structured_output(Model)` deserializa? | Definir agente con json_schema(IntentResult), invocar y verificar Pydantic validation | Si strict no funciona, usar json_object + Pydantic validation defensiva en middleware |
| S5 | Propagación W3C `traceparent` end-to-end | ¿La traza llega a App Insights con todos los spans correlacionados (browser → APIM → Host → Foundry → MCP → SQL)? | Hacer una request E2E y abrir Transaction search en App Insights | Insertar manualmente `traceparent` en cada hop si Foundry no lo propaga; documentar el gap |
| S6 | `WorkflowBuilder` con `add_edge(..., condition=lambda)` y FoundryAgent | ¿El routing condicional sobre el output tipado del agente funciona? | Workflow con 2 agentes y un condition, verificar que el routing es correcto | Construir el routing como executor custom (función Python) que recibe el output e invoca el siguiente |
| S7 | Streaming SSE end-to-end | ¿Los `WorkflowEvent` se emiten en streaming y llegan al browser? | Endpoint FastAPI con `workflow.run_stream()`, cliente curl con `-N`, verificar eventos | Polling en lugar de SSE como fallback temporal |
| S8 | Foundry + Private Endpoint del Azure OpenAI | ¿Foundry puede consumir el modelo a través de PE? | Configurar PE y crear un FoundryAgent que consuma el modelo | Mantener Azure OpenAI con acceso público restringido por IP allowlist de Foundry |

**Output del Sprint 0**: documento "spike-results.md" con uno de tres veredictos por spike: **GREEN** (sigue diseño tal cual), **AMBER** (ajuste menor identificado), **RED** (plan B activado, diseño revisado).

---

## 10. Plan de construcción de la PoC

### 10.1 Tabla de fases

| Fase | Entregable | Días |
|------|-----------|------|
| **0a** | **Spike Sprint 0** (sección 9.6) — validar suposiciones técnicas | 5 |
| 0b | Bicep + azd: VNET, ACA env, App Insights, Cosmos, Blob, KV, OpenAI, Foundry, SQL | 5 |
| 1 | MCP Schema Provider Python + tests + despliegue en ACA | 7 |
| 2 | MCP SQL Executor Python + las 4 capas + despliegue + smoke test contra SQL | 10 |
| 3 | Definición de los 3 agentes en Foundry Studio + JSON schemas | 4 |
| 4 | Agent Host Python: Workflow + 3 FoundryAgent + middleware + SSE + propagación user context | 10 |
| 5 | Integración con Angular UI (mismo contrato + SSE) | 4 |
| 6 | Observabilidad end-to-end: dashboards, alertas, audit logs | 5 |
| 7 | Hardening (PE en todo, KV refs, RBAC review, pentest interno) | 7 |
| 8 | Pruebas E2E + tuning de prompts + tuning de timeouts | 5 |
| **Total** | | **≈ 62 días laborables (≈ 13 semanas)** |

### 10.2 Criterios de aceptación por fase ("Definition of Done")

**Fase 0a — Spike**
- Todos los spikes S1–S8 con veredicto documentado en `spike-results.md`.
- Cualquier RED tiene plan B aplicado y aprobado por el tech lead.

**Fase 0b — Infra**
- `azd up` despliega todo desde cero en <30 min.
- Health checks pasan en los 3 ACAs con imagen "hello world".
- App Insights recibe trazas de smoke test de cada servicio.

**Fase 1 — MCP Schema Provider**
- Las 5 tools (`list_views`, `get_schema`, `get_joins`, `get_rules`, `sample_queries`) responden correctamente.
- RBAC: usuario sin rol no ve vistas restringidas (test automatizado).
- Schemas cargados desde Blob, caché en memoria, invalidación por Event Grid.
- Cobertura de tests unitarios ≥80%.
- Trazas OTel visibles en App Insights con atributos custom.

**Fase 2 — MCP SQL Executor**
- Las 4 capas de guardrail aplicadas en orden con tests específicos por capa.
- Inyección automática de `WHERE TeamName IN (...)` verificada con SQL parsed assertions.
- Conexión a Azure SQL vía MI (sin password en código).
- Timeout 30s y row limit 1000 enforced.
- Test E2E: query válida ejecuta, query maliciosa rechazada, query sobre vista no whitelisted rechazada.

**Fase 3 — Agentes en Foundry**
- Los 3 agentes existen en Foundry Studio con versión 1.0.0 fijada.
- Schemas JSON estrictos cargados como `response_format`.
- Instrucciones revisadas y aprobadas con el partner.
- Smoke test: cada agente, invocado desde Foundry Playground, devuelve JSON válido.

**Fase 4 — Agent Host**
- `POST /chat` recibe mensaje y devuelve QueryOutput.
- Workflow ejecuta los 3 executors en orden, con routing condicional.
- Middleware operativos: PII, PromptShields, HMAC, SQL pre-val, audit.
- `x-user-context` propagado a los MCPs y verificado con HMAC.
- Tests E2E con 10 escenarios canónicos: DataQuery happy path, OutOfScope, SmallTalk, query maliciosa, prompt injection, RBAC denial, etc.

**Fase 5 — Frontend**
- Angular UI consume `/chat` con SSE.
- Muestra progreso por executor en tiempo real (Intent → SQL → Ejecutando → Resultado).
- Manejo de errores y rechazos del guardrail con mensajes claros al usuario.

**Fase 6 — Observabilidad**
- 4 dashboards en App Insights (Health, FinOps, Security, Performance) con KQL documentado.
- 5 alertas operativas configuradas y probadas con eventos sintéticos.
- Audit log queryable en Log Analytics con KQL de ejemplo entregado al partner.

**Fase 7 — Hardening**
- Pentest interno superado (sin findings críticos ni high).
- Todos los secretos en Key Vault con MI access.
- Private Endpoints habilitados en SQL, OpenAI, KV, Storage, Cosmos.
- RBAC review documentada y firmada.

**Fase 8 — Tuning**
- P95 latency E2E < 4s.
- Coste por request < umbral acordado con el partner.
- Rate de `guardrail.violation` < 1% en escenarios benignos del corpus de test.

### 10.3 Definition of Done del proyecto completo

1. Una request E2E desde Angular hasta Azure SQL funciona y devuelve un resultado correcto.
2. Las 4 capas de defensa rechazan tráfico malicioso en pruebas dedicadas.
3. Cualquier ingeniero del partner puede abrir un trace en App Insights y entender cada paso del workflow sin ayuda.
4. Cualquier no-developer del partner puede ajustar el prompt de un agente en Foundry Studio y desplegar la nueva versión sin tocar código.
5. La documentación del repo permite a un nuevo desarrollador desplegar el sistema completo en <1 día.

---

## 11. Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|-----------|
| MAF aún es joven (GA Q4 2025), APIs pueden evolucionar | Pinear versiones, suscribirse a release notes, evitar APIs marcadas experimental |
| `FoundryAgent` con local MCP tools — la integración exacta puede variar | Validar en sprint 0 con un spike contra el sample oficial `foundry_chat_client_with_local_mcp.py` |
| HMAC key compromise | Rotación 90 días via KV, alertas si KV access anómalo |
| LLM hallucina vistas inexistentes | Schema MCP devuelve solo vistas reales; SQL Builder middleware valida que `plan.views ⊆ list_views()` |
| Coste de tokens | Prompt caching, gpt-4o-mini en Intent y Executor, monitorización FinOps en dashboards |
| Latencia MCP intra-VNET | Pool de conexiones HTTP/2, MCPs y Agent Host en el mismo ACA Environment |

---

## 12. Resumen ejecutivo

| Decisión | Justificación |
|----------|---------------|
| **MAF (Python) + Foundry Agent Service** | MAF orquesta, FAS persiste y versiona los agentes con UI propia para ajustes |
| **3 agentes especializados** (no uno) | Defense in depth, mínimo privilegio, auditoría granular |
| **MCP Schema Provider + MCP SQL Executor en ACA** | Desacoplado de Foundry; metadata y ejecución bajo control completo |
| **Workflow secuencial con routing condicional** | Refleja el flujo determinista; type safety + streaming + checkpointing |
| **MAF middleware (Capa 2)** | Atajos preventivos (PII, prompt shields, HMAC, SQL pre-val) sin tocar el resto del sistema |
| **HMAC firma/verifica SqlPlan** | Garantía de integridad del plan entre SQL Builder y Executor |
| **OpenTelemetry end-to-end** | Cada span correlacionado por `traceparent`; dashboards de health, FinOps, security, performance |
| **Mismo Frontend + APIM** | Cero impacto en UX y políticas existentes |

Esta propuesta es implementable en aproximadamente 2.5–3 meses con un equipo de 2–3 personas, partiendo de una base sólida (todos los componentes son GA en Azure) y con un perfil de riesgo controlado gracias al Spike Sprint 0.

---

## 13. Glosario

| Término | Definición |
|---------|-----------|
| **ACA** | Azure Container Apps — servicio gestionado para contenedores con auto-scaling, networking VNET, scale-to-zero |
| **AgentMiddleware** | Tipo de middleware MAF que intercepta el run completo de un agente (antes/después) |
| **AgentSession / AgentThread** | Estado conversacional persistido entre turnos del agente |
| **APIM** | Azure API Management — gateway con AuthN, rate limiting, policies |
| **Capa 1/2/3/4** | Las 4 capas de defensa en profundidad (sección 3) |
| **ContextVar** | Mecanismo Python para variables locales por async task / request |
| **FoundryAgent** | Clase MAF que actúa como cliente de un agente persistido en Foundry Agent Service |
| **Foundry Agent Service (FAS)** | Servicio gestionado de Azure AI Foundry donde se persisten definiciones de agentes |
| **FunctionMiddleware** | Tipo de middleware MAF que intercepta cada tool/function call |
| **Guardrail** | Validación de seguridad o políticas aplicada antes/después de una operación |
| **HITL** | Human-in-the-Loop — pausa del workflow para aprobación humana |
| **HMAC** | Hash-based Message Authentication Code — firma criptográfica para integridad+autenticidad |
| **Hosted MCP** | Modo donde Foundry hace la conexión al MCP server directamente |
| **Local MCP** | Modo donde el Agent Host hace la conexión al MCP server (el cliente vive en tu código) |
| **MAF** | Microsoft Agent Framework — framework GA de Microsoft para construir agentes |
| **Managed Identity (MI)** | Identidad gestionada por Azure para autenticar servicios sin secretos |
| **MCP** | Model Context Protocol — protocolo estándar para exponer tools/recursos a LLMs |
| **MCPStreamableHTTPTool** | Cliente MCP de MAF Python para conectar a un MCP server vía HTTP+SSE |
| **OBO** | On-Behalf-Of flow — patrón AAD para tokens delegados entre servicios |
| **OTel / OpenTelemetry** | Estándar abierto de observabilidad (traces, logs, metrics) |
| **PE** | Private Endpoint — endpoint privado de un servicio Azure dentro de tu VNET |
| **Prompt Shields** | Servicio de Azure Content Safety para detectar prompt injection y jailbreak |
| **RBAC** | Role-Based Access Control |
| **SqlPlan** | DTO Pydantic que el SQL Builder produce y el Executor consume, firmado con HMAC |
| **SSE** | Server-Sent Events — protocolo de streaming HTTP unidireccional |
| **Structured Outputs** | Característica de Azure OpenAI que fuerza salida JSON conforme a un schema estricto |
| **Superpaso** | Unidad de ejecución de un Workflow en MAF; checkpoint boundary |
| **traceparent** | Header W3C que correlaciona spans entre servicios |
| **Workflow** | Grafo dirigido de executors en MAF con type safety y observabilidad |

---

## 14. Referencias

### Microsoft Agent Framework
- Repo: https://github.com/microsoft/agent-framework
- Docs: https://learn.microsoft.com/en-us/agent-framework/
- Quick start: https://learn.microsoft.com/en-us/agent-framework/tutorials/quick-start
- Workflows overview: https://learn.microsoft.com/en-us/agent-framework/user-guide/workflows/overview
- Migración desde Semantic Kernel: https://learn.microsoft.com/en-us/agent-framework/migration-guide/from-semantic-kernel
- Migración desde AutoGen: https://learn.microsoft.com/en-us/agent-framework/migration-guide/from-autogen

### Samples Python de referencia
- Workflow básico con agentes: `python/samples/03-workflows/_start-here/step2_agents_in_a_workflow.py`
- FoundryAgent con function tools: `python/samples/02-agents/providers/foundry/foundry_agent_with_function_tools.py`
- FoundryChatClient con MCP local: `python/samples/02-agents/providers/foundry/foundry_chat_client_with_local_mcp.py`
- Middleware class-based: `python/samples/02-agents/middleware/class_based_middleware.py`
- Observability: `python/samples/02-agents/observability/agent_observability.py`

### Model Context Protocol
- Spec: https://modelcontextprotocol.io/
- Python SDK: https://github.com/modelcontextprotocol/python-sdk
- FastMCP: https://github.com/jlowin/fastmcp

### Azure
- Container Apps: https://learn.microsoft.com/azure/container-apps/
- AI Foundry: https://learn.microsoft.com/azure/ai-foundry/
- Content Safety (Prompt Shields): https://learn.microsoft.com/azure/ai-services/content-safety/concepts/jailbreak-detection
- Azure Monitor OpenTelemetry: https://learn.microsoft.com/azure/azure-monitor/app/opentelemetry-overview
- azd (Azure Developer CLI): https://learn.microsoft.com/azure/developer/azure-developer-cli/

---

## 15. Cómo leer este documento (instrucciones para el agente ejecutor)

Si vas a usar este documento como brief para construir la PoC, este es el orden recomendado:

1. **Lee secciones 0–3** para entender vocabulario y decisiones arquitectónicas.
2. **Ejecuta primero el Sprint 0 (sección 9.6)** — NO empieces a construir sin haber validado los spikes. Si algún spike sale RED, ajusta el diseño antes de avanzar.
3. **Usa la sección 9 como checklist** de recursos, identidades, paquetes y variables de entorno.
4. **La sección 4** tiene los esqueletos de código que puedes usar como punto de partida; espera que algunas APIs hayan evolucionado y ajústalas con los samples de la sección 14.
5. **La sección 7** describe el comportamiento esperado E2E; úsala como referencia para tests E2E.
6. **La sección 8** define la observabilidad obligatoria — todo span/log/métrica descrito ahí es parte del entregable.
7. **La sección 10** tiene la "Definition of Done" por fase. No marques una fase como completa si no cumple sus criterios.

### Preguntas a aclarar con el partner antes de empezar

1. ¿Tienen ya un tenant Entra ID configurado y permisos para crear las identidades requeridas?
2. ¿Cuál es el umbral aceptable de coste por request (para definir budget de Fase 8)?
3. ¿Las vistas de Azure SQL (`vw_PersonDetail`, etc.) ya existen o hay que crearlas?
4. ¿Tienen contrato fijo con Azure OpenAI o usaremos pay-as-you-go en la PoC?
5. ¿Permiten conectividad Foundry → Azure OpenAI vía PE o necesitamos public endpoint restringido?
6. ¿Quién mantendrá los prompts de los agentes en Foundry Studio tras el handover?
7. ¿La rotación de la HMAC key debe automatizarse o lo gestiona SecOps manualmente?

