# MPP (Machine Payments Protocol) -- Deep Research for Sardis Hackathon

**Date:** 2026-03-19
**Sources:** mpp.dev docs, GitHub repos (tempoxyz/mpp, tempoxyz/mpp-specs, wevm/mppx, solana-foundation/solana-mpp-sdk), ecosystem projects

---

## Table of Contents

1. [Protocol Overview](#1-protocol-overview)
2. [Streamed Payments (SSE)](#2-streamed-payments-sse)
3. [Pay-As-You-Go Sessions](#3-pay-as-you-go-sessions)
4. [Multi-Method Payments](#4-multi-method-payments)
5. [Proxy Pattern (mppx/proxy)](#5-proxy-pattern-mppxproxy)
6. [MCP Transport (AI Tool Calls)](#6-mcp-transport-ai-tool-calls)
7. [Custom Payment Methods](#7-custom-payment-methods)
8. [Ecosystem & Open Source Projects](#8-ecosystem--open-source-projects)
9. [Hackathon Application: Sardis Guard + MPP](#9-hackathon-application-sardis-guard--mpp)

---

## 1. Protocol Overview

### What is MPP?

MPP is an **open protocol proposed to the IETF** (not a proprietary API) that standardizes HTTP `402 Payment Required` for machine-to-machine payments. It was launched publicly on **2026-03-18** by Tempo Labs and Stripe.

**Core spec:** https://paymentauth.org (IETF draft: `draft-ryan-httpauth-payment`)

### How the Protocol Works

The protocol uses a **Challenge-Credential-Receipt** flow built on standard HTTP:

```
Client                                          Server
  |                                               |
  |--- GET /resource ----------------------------->|
  |                                               |
  |<-- 402 Payment Required ----------------------|
  |    WWW-Authenticate: Payment                  |
  |    id="ch_abc", method="tempo",               |
  |    intent="charge",                           |
  |    request="{amount, currency, recipient}"    |
  |                                               |
  |    [Client fulfills payment off-band]         |
  |                                               |
  |--- GET /resource ----------------------------->|
  |    Authorization: Payment credential="..."    |
  |                                               |
  |<-- 200 OK ------------------------------------|
  |    Payment-Receipt: ...                       |
  |    [Resource body]                            |
```

### Key Protocol Primitives

| Primitive | Purpose | HTTP Header |
|-----------|---------|-------------|
| **Challenge** | Server tells client what payment is needed | `WWW-Authenticate: Payment ...` |
| **Credential** | Client proves payment was made | `Authorization: Payment credential="..."` |
| **Receipt** | Server acknowledges payment | `Payment-Receipt: ...` |

### Two Intent Types

1. **`charge`** -- One-time payment, settles immediately on-chain
2. **`session`** -- Payment channel with off-chain vouchers for high-frequency metered billing

### Supported Payment Methods (Production)

| Method | Intent Types | Settlement |
|--------|-------------|------------|
| **Tempo** | charge, session | Stablecoins on Tempo blockchain (~500ms finality) |
| **Stripe** | charge | Cards/wallets via Shared Payment Tokens (SPTs) |
| **Lightning** | charge, session | Bitcoin via BOLT11 invoices |
| **Card** | charge | Encrypted network tokens |
| **Solana** | charge, session | SOL/SPL tokens (community SDK) |
| **Custom** | any | Build your own via `Method.from()` |

### Official SDKs

| SDK | Package | Repo |
|-----|---------|------|
| TypeScript | `mppx` (~v0.4.2) | [wevm/mppx](https://github.com/wevm/mppx) (44 stars) |
| Python | `pympp` | [tempoxyz/pympp](https://github.com/tempoxyz/pympp) (11 stars) |
| Rust | `mpp` | [tempoxyz/mpp-rs](https://github.com/tempoxyz/mpp-rs) (38 stars) |
| Solana | `solana-mpp-sdk` | [solana-foundation/solana-mpp-sdk](https://github.com/solana-foundation/solana-mpp-sdk) (30 stars) |

### Security Model

- TLS 1.2+ required for all payment flows
- Single-use payment proofs (replay protection built-in)
- Body digest binding for POST/PUT/PATCH requests (prevents request tampering)
- Idempotency keys for non-idempotent methods
- `Cache-Control: no-store` on 402 responses
- Credentials are bearer tokens -- must never be logged

---

## 2. Streamed Payments (SSE)

**Source:** https://mpp.dev/guides/streamed-payments

### How It Works

Streamed payments extend pay-as-you-go sessions with **Server-Sent Events (SSE)**. The server charges per token/word/unit as content streams. If the payment channel balance runs out mid-stream, the client automatically sends a new voucher and the stream resumes.

### Architecture

1. Client opens a Tempo session (deposits funds into on-chain escrow)
2. Server starts streaming SSE events
3. For each unit (word, token, byte), server calls `stream.charge()`
4. Client signs off-chain vouchers with increasing cumulative amounts
5. If balance runs out, client auto-tops-up and stream continues
6. Settlement happens in batches on-chain

### Server Code (Next.js)

```ts
import { Mppx, tempo } from "mppx/nextjs";

const mppx = Mppx.create({
  methods: [
    tempo({
      currency: "0x20c0000000000000000000000000000000000000", // pathUSD
      recipient: "0xYOUR_ADDRESS",
      sse: true,  // Enable SSE support
    }),
  ],
});

export const GET = mppx.session({ amount: "0.001", unitType: "word" })(
  async () => {
    const words = ["Hello", "world", "from", "streamed", "payments"];
    return async function* (stream) {
      yield JSON.stringify({ title: "Demo" }); // metadata, free
      for (const word of words) {
        await stream.charge();  // Charges $0.001 per word
        yield word;
      }
    };
  },
);
```

### Client Code

```ts
import { Mppx, tempo } from 'mppx/client'
import { privateKeyToAccount } from 'viem/accounts'

Mppx.create({
  methods: [tempo({ account: privateKeyToAccount('0x...') })],
})

// globalThis.fetch is now payment-aware
const response = await fetch('https://api.example.com/stream')
// Automatically handles 402, opens session, signs vouchers per chunk
```

### Hackathon Relevance for Sardis

**YES -- this is perfect for pay-per-evaluation streaming.** The SSE pattern maps directly to:
- Pay-per-token LLM inference billing
- Pay-per-evaluation AI agent task streaming
- Real-time metered API access

Key insight: voucher verification is CPU-bound (single `ecrecover` call), adding only microseconds per token. No RPC calls during streaming.

---

## 3. Pay-As-You-Go Sessions

**Source:** https://mpp.dev/guides/pay-as-you-go + https://mpp.dev/payment-methods/tempo/session

### How Sessions Work Technically

Sessions use **unidirectional payment channels** on Tempo's `TempoStreamChannel` escrow contract:

1. **Open:** Client deposits tokens into on-chain escrow. Creates a channel between client (payer) and server (payee). Returns a unique `channelId`.

2. **Session:** Client signs EIP-712 vouchers with increasing cumulative amounts. Each voucher says "I have now consumed up to X total." Server verifies with a single `ecrecover` -- no RPC calls, no database writes in the hot path.

3. **Top Up:** If channel runs low, client deposits more tokens without closing. Session continues uninterrupted.

4. **Close:** Either party calls `close()` on the escrow contract with the highest voucher. Settles final balance on-chain. Refunds unused deposit to client.

### Why Tempo Is Uniquely Good for Sessions

- ~500ms finality for channel lifecycle operations
- Sub-cent fees for open/close
- 2D nonce system (payment lane doesn't block other account activity)
- 100K+ TPS handles settlement volume
- Fee sponsorship (server can pay channel fees for clients)
- TIP-20 tokens are precompile-based (cheaper than ERC-20)

### Escrow Contract Addresses

| Network | Chain ID | Address |
|---------|----------|---------|
| Mainnet | 4217 | `0x33b901018174DDabE4841042ab76ba85D4e24f25` |
| Testnet (Moderato) | 42431 | `0xe1c4d3dce17bc111181ddf716f75bae49e61a336` |

### Server Example (Pay-Per-Photo)

```ts
import { Mppx, tempo } from 'mppx/nextjs'

const mppx = Mppx.create({
  methods: [tempo({
    currency: '0x20c0000000000000000000000000000000000000', // pathUSD
    recipient: '0xYOUR_ADDRESS',
  })],
})

export const GET =
  mppx.session({ amount: '0.01', unitType: 'photo' })
  (async () => {
    const res = await fetch('https://picsum.photos/200/200')
    return Response.json({ url: res.url })
  })
```

### Hackathon Relevance for Sardis

Sessions are the ideal billing model for our Guard service:
- Agent opens a payment channel once
- Each policy evaluation costs e.g. $0.001
- Server verifies vouchers in microseconds
- Settlement batched periodically
- Channel stays open for reuse across requests

---

## 4. Multi-Method Payments

**Source:** https://mpp.dev/guides/multiple-payment-methods

### How It Works

When multiple methods are registered, the 402 response includes a `WWW-Authenticate` header for **each** method. The client picks whichever rail it supports:

```http
HTTP/1.1 402 Payment Required
WWW-Authenticate: Payment method="tempo", intent="charge", ...
WWW-Authenticate: Payment method="stripe", intent="charge", ...
WWW-Authenticate: Payment method="lightning", intent="charge", ...
```

The route handler stays the same regardless of which method the client chose.

### Server Code (All Three Methods)

```ts
import Stripe from 'stripe'
import { Mppx, tempo, stripe } from 'mppx/server'
import { spark } from '@buildonspark/lightning-mpp-sdk/server'

const stripeClient = new Stripe(process.env.STRIPE_SECRET_KEY!)

const mppx = Mppx.create({
  methods: [
    tempo({
      currency: '0x20c0000000000000000000000000000000000000',
      recipient: '0xYOUR_ADDRESS',
    }),
    stripe.charge({
      client: stripeClient,
      networkId: 'internal',
      paymentMethodTypes: ['card'],
    }),
    spark.charge({
      mnemonic: process.env.MNEMONIC!,
    }),
  ],
})

// Route handler is IDENTICAL regardless of payment method
Bun.serve({
  async fetch(request) {
    const result = await mppx.charge({
      amount: '0.01',
      currency: 'usd',
      decimals: 2,
      description: 'Premium API access',
    })(request)

    if (result.status === 402) return result.challenge
    return result.withReceipt(Response.json({ message: 'Paid content' }))
  },
})
```

### Can Our Guard Accept Both Tempo AND Stripe?

**YES, absolutely.** MPP's multi-method support is additive:
- Each payment method is independent
- You can start with Tempo and add Stripe later without changing route handlers
- The client decides which rail to use based on what it supports

This means:
- AI agents with Tempo wallets pay via stablecoins
- Traditional apps with Stripe pay via cards
- Same endpoint, same API, same business logic

### Stripe Integration Details

Stripe uses **Shared Payment Tokens (SPTs)** for MPP:
- Client creates an SPT via Stripe.js
- Server creates a Stripe `PaymentIntent` using the SPT
- Settlement completes through Stripe's payment rails
- Configuration: `networkId` (Stripe Business Network ID) + `paymentMethodTypes`

---

## 5. Proxy Pattern (mppx/proxy)

**Source:** https://mpp.dev/sdk/typescript/proxy

### How the Proxy Works

The `Proxy` from `mppx/proxy` gates upstream API services behind MPP 402 payments. It handles:
- Routing requests to upstream services
- Credential injection (API keys for upstream)
- Payment verification before forwarding
- Discovery endpoints for service documentation

### Architecture

```
Client (agent) ----> MPP Proxy (your server) ----> Upstream API (OpenAI, Anthropic, etc.)
                    |                           |
                    | 1. Return 402 challenge    |
                    | 2. Verify payment          |
                    | 3. Forward to upstream     |
                    | 4. Return response+receipt |
```

### Multi-Service Proxy Example

```ts
import { Proxy, anthropic, openai, stripe } from 'mppx/proxy'
import { Mppx, tempo } from 'mppx/server'

const mppx = Mppx.create({ methods: [tempo()] })

const proxy = Proxy.create({
  description: 'Multi-service paid API proxy',
  title: 'My Proxy',
  services: [
    openai({
      apiKey: process.env.OPENAI_API_KEY!,
      routes: {
        'POST /v1/chat/completions': mppx.charge({ amount: '0.05' }),
        'GET /v1/models': true,  // free passthrough
      },
    }),
    anthropic({
      apiKey: process.env.ANTHROPIC_API_KEY!,
      routes: {
        'POST /v1/messages': mppx.charge({ amount: '0.03' }),
      },
    }),
  ],
})

// Routes automatically:
// POST /openai/v1/chat/completions -> $0.05 charge
// GET  /openai/v1/models          -> free
// POST /anthropic/v1/messages     -> $0.03 charge
```

### Built-in Service Presets

| Preset | Auth Method | Upstream |
|--------|------------|----------|
| `openai()` | `Authorization: Bearer` | api.openai.com |
| `anthropic()` | `x-api-key` | api.anthropic.com |
| `stripe()` | `Authorization: Basic` | api.stripe.com |
| `Service.from()` | Custom (bearer/headers/rewriteRequest) | Any URL |

### Custom Service Definition

```ts
import { Service } from 'mppx/proxy'

Service.from('sardis-guard', {
  baseUrl: 'https://api.sardis.sh',
  bearer: process.env.SARDIS_API_KEY!,
  description: 'Policy-enforced payment guard for AI agents',
  title: 'Sardis Guard',
  routes: {
    'POST /v1/evaluate': mppx.charge({ amount: '0.001' }),
    'GET /v1/policies': true,
  },
})
```

### Discovery Endpoints (Auto-Generated)

The proxy automatically serves discovery endpoints:

| Endpoint | Description |
|----------|-------------|
| `GET /discover` | Lists all services (JSON or markdown for AI agents) |
| `GET /discover/{id}` | Details for a single service |
| `GET /llms.txt` | `llms.txt`-formatted overview |
| `GET /discover/all.md` | Full markdown listing |

AI user agents (ChatGPT, Claude, Perplexity) automatically get markdown instead of JSON.

### Can We Proxy Our Own APIs?

**YES.** Use `Service.from()` to create a custom service definition for any upstream API. This is how you'd wrap your own Sardis APIs behind MPP payment gating.

### Hackathon Relevance

The proxy pattern is extremely relevant:
1. **Sardis as a proxy:** We could build a Sardis Guard proxy that sits in front of any API and adds policy enforcement + payment
2. **Agent-facing proxy:** AI agents discover and pay for services through a single proxy endpoint
3. **Revenue model:** Charge a margin on top of upstream API costs

---

## 6. MCP Transport (AI Tool Calls)

**Source:** https://mpp.dev/protocol/transports/mcp

### How It Works

MPP defines a transport binding for MCP (Model Context Protocol) JSON-RPC, enabling payments for AI tool calls. This is how AI agents pay for tool execution.

### Encoding Mapping

| MPP Concept | HTTP Encoding | MCP Encoding |
|-------------|---------------|--------------|
| Challenge | `WWW-Authenticate` header | JSON-RPC error code `-32042` |
| Credential | `Authorization` header | `_meta.org.paymentauth/credential` |
| Receipt | `Payment-Receipt` header | `_meta.org.paymentauth/receipt` |

### Challenge (Server -> Agent)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32042,
    "message": "Payment Required",
    "data": {
      "httpStatus": 402,
      "challenges": [{
        "id": "ch_abc123",
        "realm": "search.example.com",
        "method": "tempo",
        "intent": "charge",
        "request": {
          "amount": "10",
          "currency": "usd",
          "recipient": "0xa726a1..."
        }
      }]
    }
  }
}
```

### Credential (Agent -> Server)

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "web-search",
    "arguments": {"query": "MCP protocol"},
    "_meta": {
      "org.paymentauth/credential": {
        "challenge": { ... },
        "source": "0x1234...",
        "payload": { "signature": "0xabc..." }
      }
    }
  }
}
```

### Receipt (Server -> Agent)

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [{ "type": "text", "text": "Search results..." }],
    "_meta": {
      "org.paymentauth/receipt": {
        "status": "success",
        "challengeId": "ch_abc123",
        "method": "tempo"
      }
    }
  }
}
```

### mppx MCP Client Integration

```ts
import { McpClient } from 'mppx/client'

// Wrap an existing MCP client to make it payment-aware
const wrappedClient = McpClient.wrap(existingMcpClient, {
  methods: [tempo({ account })],
})
```

### Server-Side MCP Transport

```ts
import { Transport } from 'mppx/server'

// For raw JSON-RPC servers
Transport.mcp()

// For MCP SDK-based servers
Transport.mcpSdk()
```

### Hackathon Relevance

This is directly relevant to Sardis MCP server. We could:
1. Make sardis-mcp-server payment-aware using `Transport.mcpSdk()`
2. AI agents using Claude/Cursor would pay per tool call
3. The Guard could be an MCP tool that requires payment

---

## 7. Custom Payment Methods

**Source:** https://mpp.dev/payment-methods/custom

### How to Build a Custom Method

MPP supports building custom payment methods via `Method.from()`. You define:
1. Method name & intent
2. Request schema (what server asks for)
3. Payload schema (what client provides as proof)
4. Client logic (`createCredential`)
5. Server logic (`verify`)

### Example: Custom Lightning Method

```ts
import { Method, z } from 'mppx'

const lightning = Method.from({
  intent: 'charge',
  name: 'lightning',
  schema: {
    credential: {
      payload: z.object({ preimage: z.string() }),
    },
    request: z.object({
      amount: z.string(),
      currency: z.string(),
      invoice: z.string(),
      paymentHash: z.string(),
      recipient: z.string(),
    }),
  },
})
```

### Hackathon Relevance

We could create a **custom "sardis" payment method** that:
- Uses Sardis spending mandates as the credential
- Verifies the mandate chain before allowing payment
- Integrates with our existing policy engine

---

## 8. Ecosystem & Open Source Projects

### Official Repos

| Repo | Stars | Description |
|------|-------|-------------|
| [wevm/mppx](https://github.com/wevm/mppx) | 44 | TypeScript SDK (primary) |
| [tempoxyz/mpp-specs](https://github.com/tempoxyz/mpp-specs) | 30 | IETF specifications |
| [tempoxyz/mpp-rs](https://github.com/tempoxyz/mpp-rs) | 38 | Rust SDK |
| [tempoxyz/pympp](https://github.com/tempoxyz/pympp) | 11 | Python SDK |
| [tempoxyz/mpp](https://github.com/tempoxyz/mpp) | - | Documentation site + service directory |

### Notable Community Projects

#### 1. solana-mpp-sdk (Solana Foundation, 30 stars)
- **What:** Solana payment method for MPP (charge + session)
- **Notable:** Native SOL and SPL token transfers, fee sponsorship, Swig smart wallet integration
- **Status:** Under active development, spec not finalized
- **Hackathon use:** Could reference their session/voucher architecture for our Sardis approach

#### 2. fastapi-mpp (SylvainCostes, 1 star)
- **What:** FastAPI middleware for MPP -- Python decorator-based payment gating
- **Package:** `pip install fastapi-mpp` (with extras: `[tempo]`, `[stripe]`, `[redis]`)
- **Notable:** Redis-backed replay protection, session budgets, HMAC-signed session tokens
- **Code:**
  ```python
  from mpp_fastapi.core import MPP

  mpp = MPP(store=RedisStore(redis_url="redis://localhost:6379/0"))

  @app.get("/premium")
  @mpp.charge(amount="0.05", currency="USD", description="Premium data")
  async def premium(request: Request):
      return {"data": "paid content"}
  ```
- **Hackathon use:** DIRECT integration with our FastAPI backend. We could use this as our server-side MPP implementation.

#### 3. OnlyGate (Kenny50, hackathon project)
- **What:** Zero-trust Human-in-the-Loop (HITL) wrapper for MPP
- **Thesis:** "Tempo controls *How Much* and *To Whom*. OnlyGate controls *What* and *Why*."
- **Architecture:** Out-of-band CLI wrapper that intercepts `tempo request` commands, applies ABAC policy, routes to human approval for high-value transactions
- **Hackathon use:** THIS IS A DIRECT COMPETITOR to our Sardis Guard concept. Key differences:
  - OnlyGate is a CLI wrapper (crude interception), Sardis is SDK-level
  - OnlyGate uses binary auto-approve/human-escalate, Sardis has rich policy engine
  - OnlyGate is a hackathon project, Sardis has production architecture
  - **WE ARE BETTER** -- Sardis does programmatic policy enforcement, not just human HITL

#### 4. AgentMart (teckedd-code2save, 1 star)
- **What:** Autonomous AI agent economy -- agents hire agents and pay each other
- **Architecture:** Master orchestrator breaks down tasks, hires specialist agents, pays each one
- **Status:** Payments are currently **simulated** (stubs), architecture is MPP-ready
- **Hackathon use:** Reference architecture for multi-agent economy with payment flows

#### 5. Other Notable Projects

| Project | Description | Language |
|---------|-------------|----------|
| mpp-avalanche | Streaming payment channels on Avalanche | HTML |
| mpp-solana (starc007) | Solana SPL token payments for MPP | TypeScript |
| mpp-near | NEAR payment provider for MPP with gasless payments | Rust |
| mpp-ton | TON payment method for MPP | TypeScript |
| mpp-xpr | XPR Network payment method for MPP | TypeScript |
| mpp-movement | MPP on Movement Network | Rust |
| dexter-mpp | Managed Solana settlement for MPP | TypeScript |
| observer-protocol/mpp-integration | Trust layer for machine payments | Python |
| mpcp-protocol/mpcp-policy-authority | Policy authority for Machine Payment Control Protocol | TypeScript |

---

## 9. Hackathon Application: Sardis Guard + MPP

### What We Should Build

Based on this research, here is the recommended architecture for the hackathon:

### Architecture: Sardis Policy Guard as an MPP-Native Service

```
AI Agent (with mppx client)
    |
    |-- fetch('https://guard.sardis.sh/v1/evaluate')
    |   [Automatic 402 handling via mppx]
    |
    v
Sardis Guard Server (mppx/server + fastapi-mpp)
    |
    |-- 1. Return 402 Challenge (Tempo + Stripe methods)
    |-- 2. Verify payment credential
    |-- 3. Evaluate spending policy
    |-- 4. Return policy verdict + receipt
    |
    v
[Agent proceeds with approved transaction]
```

### Key Technical Decisions

#### 1. Use Streamed Payments for Evaluation Streaming
- `mppx.session({ amount: '0.001', unitType: 'evaluation' })`
- Agent pays per policy evaluation
- Session stays open for reuse across multiple evaluations
- Voucher verification adds microseconds, not milliseconds

#### 2. Accept Both Tempo AND Stripe
```ts
const mppx = Mppx.create({
  methods: [
    tempo({
      currency: '0x20c0000000000000000000000000000000000000',
      recipient: SARDIS_RECIPIENT,
      sse: true,
    }),
    stripe.charge({
      client: stripeClient,
      networkId: 'internal',
      paymentMethodTypes: ['card'],
    }),
  ],
})
```

#### 3. Build a Sardis Proxy for AI APIs
Use `mppx/proxy` to create a Sardis-powered proxy that:
- Wraps upstream AI APIs (OpenAI, Anthropic)
- Enforces Sardis spending policies BEFORE forwarding requests
- Charges agents via MPP for policy enforcement
- Provides discovery endpoints so agents can find and understand the service

```ts
import { Proxy, Service } from 'mppx/proxy'

const proxy = Proxy.create({
  title: 'Sardis Guard Proxy',
  description: 'Policy-enforced AI API access for autonomous agents',
  services: [
    Service.from('sardis-guard', {
      baseUrl: 'https://api.sardis.sh',
      routes: {
        'POST /v1/evaluate': mppx.session({ amount: '0.001' }),
        'POST /v1/mandates': mppx.charge({ amount: '0.01' }),
        'GET /v1/policies': true,
      },
    }),
  ],
})
```

#### 4. Python Backend via fastapi-mpp
For our FastAPI backend, use the `fastapi-mpp` package directly:
```python
from mpp_fastapi.core import MPP
from mpp_fastapi.stores import RedisStore

mpp = MPP(store=RedisStore(redis_url=os.getenv("MPP_REDIS_URL")))

@app.post("/v1/evaluate")
@mpp.charge(amount="0.001", currency="USD", description="Policy evaluation")
async def evaluate_policy(request: Request):
    # Sardis policy engine evaluates the spending mandate
    return {"verdict": "approved", "policy_id": "pol_xxx"}
```

#### 5. MCP Integration
Make the Sardis MCP server payment-aware:
```ts
import { Transport } from 'mppx/server'

// Sardis MCP tools now require payment
const transport = Transport.mcpSdk()
```

### Competitive Differentiation vs. OnlyGate

| Feature | OnlyGate | Sardis Guard |
|---------|----------|--------------|
| Integration | CLI wrapper (hijacks `tempo` command) | SDK-level, framework middleware |
| Policy | Binary (auto-approve or human-escalate) | Rich programmatic policies (spending limits, recipient allowlists, time windows, etc.) |
| Decision model | Human-in-the-loop (slow) | Automated policy engine (fast) |
| MCP support | No | Yes (Transport.mcpSdk) |
| Multi-method | Tempo only | Tempo + Stripe + Custom |
| Session support | No | Yes (pay-as-you-go metering) |
| Audit trail | Telegram notifications | Append-only ledger |
| Production ready | Hackathon PoC | Production architecture |

### Hackathon Demo Flow

1. Create a Tempo testnet wallet via `npx mppx account create`
2. Deploy Sardis Guard as an MPP-gated service
3. Agent discovers Guard via `/discover` endpoint
4. Agent pays per-evaluation via Tempo session
5. Guard evaluates spending mandate against policy engine
6. Agent receives policy verdict + payment receipt
7. Dashboard shows real-time payment + policy activity

### Resources for Building

- **LLM context file:** https://mpp.dev/llms-full.txt (give to Claude for complete MPP context)
- **mppx examples:** https://github.com/wevm/mppx/tree/main/examples
  - `charge/` -- Payment-gated photo generation
  - `session/multi-fetch/` -- Multiple paid requests over single channel
  - `session/sse/` -- Pay-per-token LLM streaming with SSE
  - `stripe/` -- Stripe SPT charge
- **CLI testing:** `npx mppx http://localhost:3000/your-endpoint`
- **Testnet tokens:** Auto-funded via `npx mppx account create`
- **FastAPI middleware:** `pip install "fastapi-mpp[tempo]"`
- **Tempo testnet RPC:** Chain ID 42431 (Moderato)

### Key Addresses

| What | Address |
|------|---------|
| pathUSD (Tempo stablecoin) | `0x20c0000000000000000000000000000000000000` |
| TempoStreamChannel (mainnet) | `0x33b901018174DDabE4841042ab76ba85D4e24f25` |
| TempoStreamChannel (testnet) | `0xe1c4d3dce17bc111181ddf716f75bae49e61a336` |
| Sardis MPC wallet | `0x99085505f506576c5C5342cAFEf14d6be43e0E9C` |
