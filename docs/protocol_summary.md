# Sardis Protocol Specification v1.1 -- Comprehensive Summary

> Prepared for The Synthesis Hackathon at Paradigm's office, March 2026.
> Source: Sardis_Complete_Protocol_v1.1.pdf (71 pages, v1.0 core + v1.1 Internal Ledger Addendum)

---

## Table of Contents

1. [Executive Thesis](#1-executive-thesis)
2. [Part II -- Core Protocol Objects](#2-part-ii----core-protocol-objects)
3. [Part III -- State Machine & Flows (22 States)](#3-part-iii----state-machine--flows-22-states)
4. [Part IV -- Security Model (11 Attack Vectors)](#4-part-iv----security-model-11-attack-vectors)
5. [Part V -- Recurring Payments](#5-part-v----recurring-payments)
6. [Part VI -- Privacy (Zero-Knowledge Proofs)](#6-part-vi----privacy-zero-knowledge-proofs)
7. [Part VII -- FX Bridge & Liquidity Routing](#7-part-vii----fx-bridge--liquidity-routing)
8. [Part VIII -- Technical Architecture](#8-part-viii----technical-architecture)
9. [Part IX -- Dispute & Arbitration Protocol](#9-part-ix----dispute--arbitration-protocol)
10. [v1.1 Addendum -- Internal Ledger](#10-v11-addendum----internal-ledger)
11. [Appendix A -- Complete Object Registry (JSON Schemas)](#11-appendix-a----complete-object-registry)
12. [Hackathon Implementation Gap Analysis](#12-hackathon-implementation-gap-analysis)
13. [Demo Strategy for Paradigm](#13-demo-strategy-for-paradigm)

---

## 1. Executive Thesis

**Core claim:** A reusable funding credential (card, wallet, bank credential, API key) is the wrong primitive for the agent economy. The correct primitive is a **One-Time Payment Object**: a signed, short-lived, revocable spending capability backed by a UTXO-style funding commitment and settled over any rail.

**Positioning:** Sardis fills the gap between intent (AP2), identity (TAP), and settlement (x402). AP2 handles *what an agent wants*. TAP handles *who the agent is*. x402 handles *how micro-settlement works*. Sardis provides the **reserve-backed execution object and lifecycle state machine** that connects all three -- plus escrow, recurring billing, privacy, and FX that none of them fully cover.

**Key differentiator from existing standards:**

| Standard | What It Solves | Sardis Relationship |
|----------|---------------|---------------------|
| Google AP2 | Mandate/intent protocol, 60+ partners | Sardis mandates extend AP2's intent model; execution objects fill their settlement gap |
| Visa TAP | Cryptographic agent identity, 100+ partners | TAP signatures serve as Agent Certificate attestation; session_hash extends their verification |
| Coinbase x402 | HTTP-native stablecoin micropayments | x402 is a settlement adapter inside Sardis; their deferred payment maps to our Funding Commitment |
| Mastercard Agent Pay | Agentic tokens, registered agents | MC Agentic Tokens can be a funding source type |
| A2A Protocol | Agent-to-agent communication | Transport layer; A2A carries mandate/payment messages |
| MCP | Tool/API access for agents | Payment tools exposed as MCP servers |

---

## 2. Part II -- Core Protocol Objects

Sardis v1.0 defines **10 protocol objects** forming a complete audit chain from delegation through settlement. v1.1 adds 4 more (MerchantAccount, LedgerEntry, OnRampDeposit, OffRampWithdrawal).

### 2.1 Agent Certificate (Section 7)

Identifies the agent and binds it to an issuer and principal context. TAP-compatible.

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `agent_id` | string (uuid) | Unique identifier for the agent |
| `issuer_id` | string | Entity that issued/registered this agent |
| `principal_id` | string | Human or enterprise behind the agent |
| `agent_public_key` | JWK | Agent's cryptographic public key (Ed25519 or P-256) |
| `attestation_type` | enum | `self_signed` / `issuer_attested` / `network_verified` |
| `trust_tier` | integer (0-3) | Higher = more trusted, higher tx limits |
| `capabilities` | string[] | Allowed action types: browse, pay, subscribe, delegate |
| `expires_at` | timestamp | Certificate expiry (max 1 year recommended) |
| `signature` | Signature | Issuer's Ed25519/P-256 signature over this certificate |

**Trust Tiers:**

| Tier | Description | Max Single Tx | Verification Required |
|------|-------------|---------------|----------------------|
| 0 | Unverified / self-signed | $10 | Email only |
| 1 | Issuer-attested | $500 | KYC-lite + issuer vouch |
| 2 | Network-verified | $10,000 | Full KYC + network registration (TAP-compatible) |
| 3 | Enterprise-grade | Policy-defined | Enterprise IAM + audit trail + continuous monitoring |

### 2.2 Spending Mandate (Section 8)

The signed statement of allowed authority from the principal. Think of it as a **programmable, cryptographically signed power of attorney for spending**. Designed to be expressible as an AP2 VDC.

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `mandate_id` | string (uuid) | Unique mandate identifier |
| `principal_id` | string | Who authorized this spend |
| `agent_id` | string | Which agent is authorized |
| `merchant_scope` | string[] | Allowed merchants or merchant classes (domains, MCC groups) |
| `category_scope` | string[] | Allowed MCC codes or product categories |
| `max_amount_per_tx` | Amount | Maximum per single transaction |
| `max_amount_per_period` | Amount | Maximum per day/week/month (per `period_type`) |
| `period_type` | enum | `daily` / `weekly` / `monthly` |
| `currency_scope` | string[] | Allowed currencies (USD, USDC, EUR...) |
| `rail_scope` | string[] | Allowed settlement rails (stablecoin, card, bank) |
| `approval_threshold` | Amount / null | Amount above which human approval is required |
| `purpose` | string | Human-readable purpose description |
| `retry_limit` | integer | Max retries per payment attempt |
| `in_flight_limit` | integer | **Max concurrent outstanding payment objects (anti-shadow-lock, T4)** |
| `fx_policy` | FXPolicy / null | Cross-currency rules: max_slippage_bps, preferred providers |
| `valid_from` | timestamp | Mandate activation time |
| `expires_at` | timestamp | Mandate expiry |
| `policy_hash` | string | SHA-256 hash of the full policy object for integrity |
| `revocation_handle` | string | Handle for revoking this mandate in real-time |
| `nonce` | string | Unique nonce for replay protection |
| `signature` | Signature | Principal's cryptographic signature (Ed25519/P-256) |

**CRITICAL SECURITY FIELD:** `in_flight_limit` prevents shadow lock attacks (T4) where a malfunctioning agent freezes all funds by requesting objects without presenting them. Agent must settle or cancel before new objects can be minted beyond this limit.

### 2.3 Funding Commitment & UTXO FundingCells (Section 9)

**Why UTXO instead of a global counter:** In v0, a Funding Commitment was a single monolithic lock against a vault balance -- a fundamental concurrency bottleneck. v1 replaces this with a **UTXO (Unspent Transaction Output) model** inspired by Bitcoin. Each cell has exactly one owner at any time. Concurrent payments claim different cells. The system scales horizontally. PostgreSQL `FOR UPDATE SKIP LOCKED` ensures concurrent transactions never block each other.

#### 2.3.1 Funding Commitment (Container)

| Field | Type | Description |
|-------|------|-------------|
| `commitment_id` | string (uuid) | Unique commitment identifier |
| `mandate_id` | string | Bound to this mandate |
| `funding_source_type` | enum | `custodial_fiat` / `smart_wallet` / `card` / `bank` / `stablecoin` / `credit_line` / `sardis_balance` (v1.1) |
| `funding_source_ref` | string | Reference to the actual funding source (vault, account, contract) |
| `total_committed` | Amount | Total amount committed for this mandate |
| `cell_strategy` | enum | `pre_split` / `on_demand` / `hybrid` |
| `default_cell_denomination` | Amount | Default size for new cells |
| `commitment_expiry` | timestamp | When the commitment expires |
| `settlement_preferences` | string[] | Preferred settlement rails, ordered by preference |
| `fallback_options` | string[] | Alternative rails if primary fails |
| `refund_destination` | string | **MUST point to permanent Principal Master Treasury** (not temp vault) |
| `issuer_signature` | Signature | Issuer/vault attestation of fund availability |

**Security: `refund_destination`** -- Always points to a permanent Principal Master Treasury, never a temporary vault or cell. Prevents refund-to-closed-vault failures (T6) when disputes resolve months after the original transaction.

#### 2.3.2 FundingCell (UTXO)

| Field | Type | Description |
|-------|------|-------------|
| `cell_id` | string (uuid) | Unique cell identifier -- primary key for locking |
| `commitment_id` | string | Parent Funding Commitment |
| `mandate_id` | string | Bound to this mandate |
| `denomination` | Amount | Fixed value of this cell |
| `state` | enum | `AVAILABLE` / `CLAIMED` / `SPENT` / `RETURNED` / `EXPIRED` / `SPLIT` / `MERGED` |
| `claimed_by` | string / null | `payment_object_id` that claimed this cell |
| `claimed_at` | timestamp / null | When the cell was claimed |
| `payment_object_id` | string / null | Associated payment object |
| `parent_cell_id` | string / null | If created by splitting a larger cell |
| `vault_ref` | string | Reference to backing vault reserve |
| `created_at` | timestamp | Cell creation time |
| `expires_at` | timestamp | Cell expiry (inherits from commitment) |
| `nonce` | string | Unique nonce for this cell |
| `issuer_signature` | Signature | Issuer attests this cell is backed by real funds |

**Cell Lifecycle:**

| State | Description | Transitions |
|-------|-------------|-------------|
| AVAILABLE | Spendable -- can be claimed by a payment | CLAIMED, SPLIT, EXPIRED |
| CLAIMED | Reserved for one specific payment object -- locked | SPENT, RETURNED |
| SPENT | Value consumed, settlement confirmed (burned) | Terminal |
| RETURNED | Payment cancelled/failed/revoked -- back to pool | AVAILABLE (re-enters pool) |
| EXPIRED | Cell expiry reached without use | Terminal (reclaimed to vault) |
| SPLIT | Divided into smaller child cells (change output) | Terminal (children created) |
| MERGED | Consolidated with other small cells (defragmentation) | Terminal (parent created) |

**Splitting & Merging:** If an agent needs $7 but the smallest available cell is $10, the system splits the $10 cell into a $7 cell (CLAIMED) and a $3 cell (AVAILABLE). This mirrors Bitcoin's change output mechanism. Background merge (defragmentation) runs when cell count for a mandate exceeds a threshold (e.g., 50 cells).

### 2.4 One-Time Payment Object (Section 10)

The single-use executable payment artifact. This is what the agent presents to the merchant. Derived from the mandate + funding commitment cell(s). Every payment creates a fresh object -- **no credential is ever reused**. This is the core innovation of the protocol.

A merchant can verify this object in three ways: **transparent** (full cleartext), **hybrid** (cleartext amount + ZKP for identity/policy), or **full ZK** (merchant learns only validity).

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `payment_object_id` | string (uuid) | Unique payment identifier |
| `mandate_id` | string | Parent mandate reference |
| `commitment_id` | string | Funding commitment reference |
| `cell_ids` | string[] | Consumed FundingCell IDs (UTXO inputs) |
| `merchant_id` | string | Bound to this specific merchant |
| `session_hash` | string | `sha256(merchant_id + cart_id + timestamp)` -- **anti-relay (T3)** |
| `exact_amount` | Amount | Exact payment amount |
| `source_currency` | string | Currency of funding (may differ from target if FX needed) |
| `target_currency` | string | Currency merchant receives |
| `nonce` | string | One-time nonce for replay protection |
| `one_time_use` | boolean | **Always true** -- single use only |
| `expires_at` | timestamp | Short-lived expiry (minutes to hours) |
| `privacy_mode` | enum | `transparent` / `hybrid` / `full_zk` |
| `zk_proof` | bytes / null | ZK proof if privacy_mode != transparent |
| `escrow_required` | boolean | Whether this payment routes through escrow |
| `escrow_profile` | EscrowProfile / null | Timeout, dispute window, evidence deadline |
| `dispute_profile` | DisputeProfile | Refund destination, arbitration endpoint, reversal eligibility |
| `signature_chain` | Signature[] | Ordered: principal_sig, issuer_sig, agent_sig |

**CRITICAL SECURITY:** `session_hash = SHA-256(merchant_id + cart_id/session_id + timestamp)`. Binds payment to a specific merchant session/cart. Prevents relay/MITM attacks (T3) where an intermediary intercepts a valid payment and uses it for their own cart.

### 2.5 Settlement Receipt (Section 11)

Canonical proof of what actually happened. Closes the audit chain. v1.0 fields + v1.1 additions.

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `receipt_id` | string (uuid) | Unique receipt identifier |
| `payment_object_id` | string | Which payment object was settled |
| `settlement_rail` | string | Which rail was actually used |
| `settlement_tx_ref` | string | External transaction reference (on-chain tx hash, Stripe charge ID, etc.) |
| `settled_amount` | Amount | Final settled amount |
| `fees` | Amount | Fee breakdown (network + protocol + FX) |
| `fx_quote_id` | string / null | Reference to FXQuote if cross-currency |
| `actual_fx_rate` | number / null | Actual conversion rate applied |
| `fx_fee` | Amount / null | FX conversion fee |
| `timestamp` | timestamp | Settlement completion time |
| `status` | enum | `settled` / `partial_settled` / `failed` / `reversed` |
| `fulfillment_status` | enum | `pending_ack` / `acknowledged` / `dispute_auto_triggered` |
| `merchant_signature` | Signature | Merchant confirmation of settlement |
| `network_signature` | Signature | Network/facilitator confirmation |
| `settlement_type` | enum (v1.1) | `internal_ledger` / `external_rail` |
| `ledger_entry_id` | string / null (v1.1) | Reference to LedgerEntry for internal settlements |

**`fulfillment_status` (new in v1):** Tracks whether the agent acknowledged receipt of service. If not acknowledged within escrow timeout, `dispute_auto_triggered` fires automatically. Prevents the "paid but not delivered" gap (T11).

### 2.6 EscrowHold (Section 12)

For transactions above escrow threshold, funds land in escrow before merchant receives them.

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `escrow_id` | string (uuid) | Unique escrow identifier |
| `payment_object_id` | string | Associated payment |
| `held_amount` | Amount | Amount in escrow |
| `held_at` | enum | `issuer_vault` / `smart_contract` / `internal_hold` (v1.1) |
| `contract_address` | string / null | On-chain escrow address if applicable |
| `beneficiary` | string | Merchant who will receive on release |
| `release_condition` | ReleaseCondition | `AGENT_CONFIRM` / `TIMELOCK` / `ORACLE` |
| `timeout_duration` | Duration (ISO 8601) | How long before auto-release |
| `auto_release_at` | timestamp | Calculated auto-release time |
| `state` | enum | `HELD` / `CONFIRMING` / `AUTO_RELEASING` / `RELEASED` / `DISPUTING` / `ARBITRATING` / `RESOLVED_*` |
| `dispute_window` | Duration | How long after release a dispute can still be filed |
| `evidence_deadline` | Duration | Deadline for evidence submission after dispute |
| `arbitration_endpoint` | URI | Where disputes are submitted |
| `issuer_signature` | Signature | Issuer attestation of escrowed funds |
| `escrow_type` | enum (v1.1) | `internal_hold` / `smart_contract` / `issuer_vault` |

**Default escrow timeouts by transaction type:**

| Transaction Type | Escrow Timeout | Dispute Window | Evidence Deadline |
|------------------|---------------|----------------|-------------------|
| API/SaaS (digital) | 1 hour | 24 hours | 3 days |
| Software license | 24 hours | 7 days | 5 days |
| Physical goods | 14 days | 30 days | 7 days |
| B2B services | 30 days | 60 days | 14 days |

### 2.7 FXQuote (Section 13)

Records the cross-currency conversion applied during settlement.

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `fx_quote_id` | string (uuid) | Unique quote identifier |
| `source_currency` | string | Currency being converted from |
| `target_currency` | string | Currency being converted to |
| `quoted_rate` | number | Conversion rate at time of quote |
| `quoted_at` | timestamp | When rate was quoted |
| `quote_valid_until` | timestamp | Quote expiry (default: 30 seconds) |
| `source_amount` | Amount | Amount debited from funding |
| `target_amount` | Amount | Amount delivered to merchant |
| `fx_fee` | Amount | Conversion fee charged |
| `total_source_debit` | Amount | source_amount + fx_fee |
| `slippage_actual_bps` | integer | Actual slippage in basis points |
| `provider` | string | Which provider executed the conversion |
| `provider_tx_ref` | string | Provider's transaction reference |

---

## 3. Part III -- State Machine & Flows (22 States)

The full payment lifecycle incorporating escrow, partial settlement, dispute arbitration, FX routing, and fulfillment acknowledgment. **This is the most comprehensive payment state machine designed for agent commerce.**

### 3.1 Complete State Table

| State | Description | Allowed Transitions |
|-------|-------------|---------------------|
| **ISSUED** | Payment object minted by issuer, cell(s) CLAIMED | PRESENTED, REVOKED, EXPIRED |
| **PRESENTED** | Agent presented object to merchant | VERIFIED, FAILED, EXPIRED |
| **VERIFIED** | Merchant verified claims (cleartext, hybrid, or ZKP) | LOCKED, ESCROWED, FAILED |
| **LOCKED** | Funds locked -- direct settlement path (below escrow threshold) | SETTLING, CANCELLED |
| **ESCROWED** | Funds in escrow hold (above threshold) | CONFIRMING, AUTO_RELEASING, DISPUTING |
| **CONFIRMING** | Agent reviewing delivery from merchant | RELEASED, DISPUTING |
| **AUTO_RELEASING** | Timelock expired without dispute, auto-releasing to merchant | RELEASED |
| **RELEASED** | Escrow released to merchant | SETTLING, DISPUTING (within dispute_window) |
| **SETTLING** | Settlement executing on chosen rail (may include FX conversion) | SETTLED, PARTIAL_SETTLED, FAILED |
| **SETTLED** | Full settlement complete | FULFILLED, DISPUTED, REFUNDED |
| **FULFILLED** | Agent acknowledged receipt of service/good (ACK) | Terminal |
| **PARTIAL_SETTLED** | Partial amount settled (less than locked) | UNLOCKING, DISPUTED |
| **UNLOCKING** | Residual funds returning to cell pool | UNLOCKED |
| **UNLOCKED** | Residual FundingCells returned to AVAILABLE state | Terminal |
| **DISPUTING** | Dispute filed, evidence collection phase | ARBITRATING |
| **ARBITRATING** | Arbitration node reviewing submitted evidence | RESOLVED_REFUND, RESOLVED_RELEASE, RESOLVED_SPLIT |
| **RESOLVED_REFUND** | Full refund to principal (dispute upheld) | Terminal |
| **RESOLVED_RELEASE** | Full release to merchant (dispute rejected) | Terminal |
| **RESOLVED_SPLIT** | Partial refund + partial release (compromise) | Terminal |
| **REVOKED** | Pre-use revocation by principal or issuer | Terminal (cells -> RETURNED) |
| **EXPIRED** | Expiry time reached before use | Terminal (cells -> RETURNED) |
| **CANCELLED** | Pre-settlement cancellation | UNLOCKING (releases locked cells) |
| **FAILED** | Processing failure at any stage | Terminal (may trigger retry if within mandate.retry_limit) |
| **REFUNDED** | Post-settlement refund issued | Terminal |

### 3.2 Happy Path Flow (16 Steps)

1. Principal authorizes a bounded spending mandate with merchant scope, amount limits, and policy.
2. Issuer creates a Funding Commitment backed by the principal's vault/treasury.
3. Agent discovers a merchant and receives a quote/cart with a `session_id`.
4. Agent requests a payment object from issuer. Issuer checks: mandate bounds, `in_flight_limit`, policy compliance.
5. Issuer claims a FundingCell via `FOR UPDATE SKIP LOCKED`. If cell > amount, splits into claimed + change.
6. Issuer obtains Settlement Clearance Lock (prevents double-settlement on multiple rails).
7. Issuer mints One-Time Payment Object with `session_hash` binding.
8. Agent presents payment object to merchant.
9. Merchant verifies: agent certificate chain, mandate scope, payment object signature, `session_hash` match, nonce freshness, expiry, merchant binding. (Transparent, hybrid, or ZKP mode.)
10. If escrow required: Funds enter EscrowHold. Merchant sees proof-of-lock, delivers service. Agent confirms receipt (or timelock auto-releases).
11. If FX needed: Liquidity Router finds best rate within `mandate.fx_policy.max_slippage_bps`.
12. Settlement Facilitator routes payment over selected backend rail (stablecoin, card, bank).
13. Settlement Receipt emitted and signed by merchant + network.
14. Agent ACKs receipt of service/good. State transitions to FULFILLED.
15. Consumed FundingCell transitions to SPENT (burned). If partial: residual cell created as AVAILABLE.
16. Audit trail records: principal > agent > mandate > commitment > cell > payment object > escrow > receipt > fulfillment.

**Key insight:** The payment object is not the rail. It is a portable authorization artifact. Settlement happens over cards, ACH, RTP, stablecoins, or future rails. New rails = just new settlement adapters.

### 3.3 Escrow Flow

```
1. Payment verified -> state = ESCROWED (not LOCKED)
2. Funds held in issuer vault or smart contract
3. Merchant receives cryptographic proof of escrow lock
4. Merchant delivers service/data/goods
5a. Agent confirms receipt -> state = RELEASED -> SETTLING -> SETTLED -> FULFILLED
5b. Timelock expires (no dispute) -> state = AUTO_RELEASING -> RELEASED -> ...
5c. Agent disputes -> state = DISPUTING -> ARBITRATING -> RESOLVED_*
```

**Rail mapping:** For card rail: escrow = auth-hold, release = capture. For stablecoin: escrow = smart contract or issuer-custodied hold. For bank: escrow = issuer-held reserve with delayed ACH push.

### 3.4 v1.1 Fast-Path (Internal Ledger)

| Path | Condition | States Traversed | Latency |
|------|-----------|-----------------|---------|
| v1.0 direct path | Below escrow, any merchant | VERIFIED -> LOCKED -> SETTLING -> SETTLED | 100ms - 2 days |
| **v1.1 internal fast-path** | Below escrow, BOTH on Sardis | **VERIFIED -> SETTLING -> SETTLED** | **~1ms (single DB transaction)** |
| v1.1 internal escrow | Above escrow, both on Sardis | VERIFIED -> ESCROWED -> CONFIRMING -> RELEASED -> SETTLING -> SETTLED | Timeout-dependent |
| v1.1 external fallback | Merchant NOT on Sardis | Same as v1.0 (all 22 states available) | Same as v1.0 |

### 3.5 Cell Claim Algorithm (Concurrency: Section 18)

The core algorithm for concurrent-safe payment minting:

```
FUNCTION mint_payment_object(mandate, merchant, amount, session_hash):

  // 1. Check in_flight_limit (anti-shadow-lock)
  pending = COUNT payment_objects WHERE mandate_id = mandate.id
    AND state IN (ISSUED, PRESENTED, VERIFIED, LOCKED, ESCROWED, SETTLING)
  IF pending >= mandate.in_flight_limit:
    RETURN ERROR("in_flight_limit_exceeded")

  // 2. Claim cell(s) -- SKIP LOCKED prevents double-claim
  cell = SELECT * FROM funding_cells
    WHERE mandate_id = mandate.id
    AND state = "AVAILABLE"
    AND denomination.value >= amount
    ORDER BY denomination.value ASC  // best-fit: smallest sufficient cell
    LIMIT 1
    FOR UPDATE SKIP LOCKED  // CRITICAL: skip already-claimed rows

  IF cell IS NULL:
    // Try combination of multiple smaller cells
    cells = select_cell_combination(mandate, amount)
    IF cells IS NULL: RETURN ERROR("insufficient_funds")

  // 3. Split if cell > amount (create change output)
  IF cell.denomination > amount:
    change_cell = create_cell(cell.denomination - amount, state=AVAILABLE)
    cell.state = SPLIT
    claimed_cell = create_cell(amount, state=CLAIMED, claimed_by=new_po_id)
  ELSE:
    cell.state = CLAIMED
    cell.claimed_by = new_po_id

  // 4. Obtain Settlement Clearance Lock (anti-double-settlement T8)
  clearance = REQUEST_CLEARANCE_LOCK(issuer, cell.id)
  IF clearance.denied: RETURN ERROR("clearance_denied")

  // 5. Mint payment object with session binding
  po = create_payment_object(
    mandate, claimed_cell, merchant, amount,
    session_hash=sha256(merchant.id + merchant.cart_id + NOW())
  )
  RETURN po
```

**Distributed scaling strategies:**

| Topology | Strategy | Throughput | Tradeoff |
|----------|----------|-----------|----------|
| Single PostgreSQL | FOR UPDATE SKIP LOCKED | ~50K claims/sec | Simplest. Phase 0-2 |
| Multi-node, shared DB | Same SQL + PgBouncer pooling | ~100K claims/sec | Linear scaling to 3-5 nodes |
| Multi-node, sharded | Shard cells by mandate_id | ~500K claims/sec | High throughput, mandate-level isolation |
| Smart contract (L2) | Each cell = on-chain UTXO, claim = atomic tx | ~1K claims/sec | Trustless, higher latency (~2s on Base) |

---

## 4. Part IV -- Security Model (11 Attack Vectors)

**Every threat has a concrete, protocol-level mitigation built into v1. This is not theoretical -- the mitigations are structural.**

### 4.1 Complete Threat Table

| ID | Threat | Attack Vector | Mitigation |
|----|--------|--------------|------------|
| **T1** | Double-Spending | Agent fires concurrent payments, all checking same balance | UTXO FundingCells -- each payment claims different cell via `FOR UPDATE SKIP LOCKED` |
| **T2** | Replay Attack | Attacker replays a valid payment object | Triple protection: unique nonce + timestamp window (5min) + session_hash binding |
| **T3** | Relay / MITM | Proxy intercepts valid payment, relays to real merchant for own cart | `session_hash = sha256(merchant_id + cart_id + timestamp)`. Object bound to specific session |
| **T4** | Shadow Lock (Self-DDoS) | Agent requests many objects without presenting them, freezing funds | `in_flight_limit` on mandate. Must settle/cancel before new minting beyond limit |
| **T5** | Revocation Propagation Lag | Agent acts in gap between revocation and merchant cache refresh | Real-time Revocation Bloom Filter via WebSocket. Max propagation target: 500ms |
| **T6** | Refund to Closed Vault | Dispute resolved months later, original vault expired | `refund_destination` always points to permanent Principal Master Treasury |
| **T7** | Usage Report Forgery | Malicious merchant inflates usage reports for recurring billing | Mandatory `agent_countersignature` on UsageReport. Agent cross-checks own logs |
| **T8** | Double-Settlement | Merchant sends same object to two settlement facilitators | Settlement Clearance Lock: facilitator must obtain one-time lock from issuer. First locks, second rejected |
| **T9** | Mandate Forgery | Attacker forges a spending mandate | Principal Ed25519/P-256 signature verification on all mandates |
| **T10** | Price Creep | SaaS vendor applies micro-increases each billing cycle under threshold | `cumulative_drift_cap_pct` (max total drift over window) + auto-escalation after N trueups |
| **T11** | Delivery Gap | Merchant paid but fails to deliver (500 error after settlement) | `fulfillment_status` + escrow timelock. Auto-dispute if agent doesn't ACK within timeout |

### 4.2 Session-Bound Anti-Relay Protection (Section 22)

Every One-Time Payment Object includes a `session_hash` that binds it to a specific merchant interaction:

```
session_hash = SHA-256(
  merchant_id +
  cart_id_or_session_id +
  timestamp_of_cart_creation
)

// Merchant verification includes:
// 1. Recompute session_hash from their own cart data
// 2. Compare with payment_object.session_hash
// 3. Reject if mismatch (relay detected)
```

### 4.3 In-Flight Limit Anti-Shadow-Lock (Section 23)

A malfunctioning agent (hallucinating, stuck in retry loop) could request hundreds of payment objects without presenting any to merchants. Each object claims a FundingCell, effectively freezing all funds until expiry. The `in_flight_limit` prevents this:

```
// Before minting new payment object:
pending_count = COUNT(*) FROM payment_objects
  WHERE mandate_id = mandate.id
  AND state IN ("ISSUED", "PRESENTED", "VERIFIED", "LOCKED", "ESCROWED", "SETTLING")

IF pending_count >= mandate.in_flight_limit:
  RETURN ERROR {
    code: "IN_FLIGHT_LIMIT_EXCEEDED",
    message: "Maximum concurrent payment objects reached. Settle or cancel existing objects.",
    current_in_flight: pending_count,
    limit: mandate.in_flight_limit
  }
```

### 4.4 Revocation Broadcast Architecture (Section 20)

Target: < 500ms end-to-end propagation.

1. Principal calls DELETE `/mandates/{id}` (or `/payment-objects/{id}`)
2. Issuer updates state to REVOKED in PostgreSQL (atomic)
3. Issuer publishes to Redis Stream: `"revocations:{issuer_id}"`
4. Revocation Broadcaster builds Bloom Filter update (incremental)
5. WebSocket broadcast to all subscribed merchants
6. Merchants update local Bloom Filter (in-memory, ~1KB)
7. On next verification, merchant checks Bloom Filter BEFORE JWKS cache:
   - IF `bloom_filter.might_contain(payment_object_id)`: FETCH fresh status from issuer (bypasses all caches)
   - ELSE: proceed with cached verification (fast path)

Bloom filter false positive rate: ~0.1% (acceptable: triggers extra check, not automatic rejection).

### 4.5 Settlement Clearance Lock (Section 21)

Prevents double-settlement (T8):

```
FUNCTION request_clearance_lock(issuer, cell_id, rail, facilitator_id):
  // Atomic operation at issuer
  existing = SELECT * FROM clearance_locks
    WHERE cell_id = cell_id FOR UPDATE

  IF existing IS NOT NULL:
    RETURN { status: "DENIED", reason: "already_locked", locked_by: existing.facilitator_id }

  INSERT INTO clearance_locks (cell_id, rail, facilitator_id, locked_at, expires_at)
    VALUES (cell_id, rail, facilitator_id, NOW(), NOW() + INTERVAL '5 minutes')

  RETURN { status: "GRANTED", lock_id: new_lock_id, expires_at: ... }

// Lock auto-expires after 5 minutes if settlement not completed
```

### 4.6 Cryptographic Design (Section 24)

- **Signature scheme:** JWS Compact Serialization (RFC 7515) with Ed25519 (preferred for speed) or ECDSA P-256 (for HSM environments)
- **Signature chain:** Each object includes signature of the signing party plus hash of parent objects for integrity verification
- **Key rotation:** Agent certificates and issuer keys support rotation via `kid` (Key ID) in JWS header. Old keys remain valid until certificate expiry. Public keys distributed via JWKS endpoint (RFC 7517)
- **Rotation frequency:** Every 90 days for issuers, per-certificate for agents

---

## 5. Part V -- Recurring Payments

> "A subscription is a long-lived spending mandate that mints short-lived one-time payment objects for each billing event. The reusable thing is the authority, never the execution credential."

### 5.1 Subscription Mandate (Section 25)

Extends the base Spending Mandate with temporal recurrence, usage semantics, adjustment rules, and lifecycle controls.

**Additional fields (beyond base SpendingMandate):**

| Field | Type | Description |
|-------|------|-------------|
| `subscription_id` | string (uuid) | Root identifier for the subscription |
| `version` | integer | Increments on amendment (plan change, price change) |
| `pricing_model` | enum | `fixed` / `usage` / `hybrid` / `tiered` |
| `max_per_charge` | Amount | Maximum per single billing event |
| `max_per_period` | Amount | Maximum per billing period |
| `max_cumulative` | Amount / null | Lifetime spending cap |
| `billing_interval` | Duration (ISO 8601) | e.g., P1M for monthly, P1W for weekly |
| `billing_anchor` | timestamp | First billing date |
| `usage_reporting_window` | Duration / null | For usage-based: how often usage is reported |
| `auto_renew` | boolean | Whether subscription auto-renews |
| `renewal_limit` | integer / null | Max consecutive renewals (null = unlimited) |
| `grace_period` | Duration / null | Failed charge retry window |
| `retry_limit` | integer | Max retries per failed charge |
| `retry_backoff` | enum | `linear` / `exponential` |
| `adjustment_rule` | AdjustmentRule | What can change without re-authorization |
| `pause_allowed` | boolean | Whether pausing is permitted |
| `cancel_notice_period` | Duration / null | Required notice for cancellation |
| `proration_on_cancel` | boolean | Issue credit on early cancellation |
| `status` | enum | `active` / `paused` / `cancelled` / `expired` / `suspended` |
| `signature` | Signature | Principal's signature |

### 5.2 Charge Intent & Mandate Trees (Section 26)

Each billing event creates a fresh Charge Intent derived from the parent Subscription Mandate. Subscriptions form a **tree**, not a flat list. Simple monthly renewals look like a straight chain, but real lifecycle events (upgrades, downgrades, retries, usage overages, proration credits) create branches.

**Integrity rules:**
1. `sequence_no` is monotonic across entire subscription
2. `previous_receipt_hash` creates audit chain
3. Retries share `sequence_no` with incremented `retry_attempt`
4. Mandate version changes create new branches in the tree

### 5.3 Usage-Based Billing & Countersignature (Section 27)

For usage-based subscriptions, the merchant submits a signed UsageReport. v1 requires the **agent to countersign** the report after cross-checking its own internal logs.

**Security rule:** No agent countersignature = no Charge Intent minted. The agent MUST verify merchant-reported usage against its own API call logs, token counts, or resource consumption records before co-signing. If discrepancy > 10%, the agent should escalate to principal instead of co-signing.

### 5.4 Subscription State Machine (Section 28)

| State | Entry Condition | Transitions |
|-------|----------------|-------------|
| ACTIVE | Subscription created and valid | PAUSED, CANCELLED, EXPIRED, SUSPENDED |
| PAUSED | Principal/agent triggers pause | ACTIVE (resume) |
| CANCELLED | Explicit cancellation | Terminal (proration credit + refund flows continue) |
| EXPIRED | expires_at reached without renewal | Terminal |
| SUSPENDED | Issuer/system action (fraud, funding failure, compliance hold) | ACTIVE (reinstatement) |

### 5.5 Price Creep Protection (Section 30)

The AdjustmentRule governs what changes without requiring re-authorization:

| Field | Type | Description |
|-------|------|-------------|
| `max_price_increase_pct` | number | Max per-cycle increase (e.g., 10 = up to 10%) |
| `cumulative_drift_cap_pct` | number | Max total drift over drift window (e.g., 25% over 6 months) |
| `cumulative_drift_window` | Duration | Window for measuring cumulative drift |
| `auto_adjust_for_usage` | boolean | Allow usage-based true-ups within ceiling |
| `auto_adjust_ceiling` | Amount | Max auto-adjusted charge |
| `consecutive_trueup_escalation` | integer | After N consecutive trueups, auto-escalate to principal |
| `reauth_required_above` | Amount | Price change above this requires new principal signature |

### 5.6 BNPL (Credit-Backed Mandates) (Section 31)

BNPL is not a separate product. It is a CreditFacility as the funding source for a purchase, plus an auto-generated Subscription Mandate for repayment. Merchant gets paid immediately via normal settlement. Principal repays in installments against their primary funding source.

---

## 6. Part VI -- Privacy (Zero-Knowledge Proofs)

### 6.1 Metadata Leakage Threat (Section 32)

In transparent mode, a One-Time Payment Object contains mandate_id, merchant_id, and exact_amount in cleartext. A merchant or settlement facilitator observing traffic can reconstruct:
- (a) Which mandates are active for a principal -- spending pattern analysis
- (b) Which merchants a principal works with -- competitive intelligence
- (c) Aggregate budget and velocity -- treasury reverse-engineering
- (d) Agent deployment patterns -- operational intelligence

**For enterprise B2B: This is a deal-breaker.** A cloud provider should not learn that a customer also buys from competitors, or what their total infrastructure budget is.

### 6.2 ZKP Verification Architecture (Section 33)

Replace cleartext verification with zero-knowledge proofs. The merchant learns only what it needs.

> The merchant's question: "Is this payment valid and backed by sufficient funds for my price?"
> The ZKP answer: "Yes." Nothing else.

### 6.3 Provable Claims (Section 34)

| Claim | What ZK Circuit Proves | What Stays Private |
|-------|----------------------|-------------------|
| Authorization | Payment was signed by a valid issuer with a valid mandate | mandate_id, principal_id, full mandate scope, other merchants |
| Sufficiency | Backing FundingCell denomination >= requested amount | Total balance, other commitments, vault details, cell count |
| Merchant Binding | Payment is bound to this specific merchant + this session | Other merchants in mandate scope, previous transactions |
| Freshness | Payment object is within validity window and nonce is unique | Exact creation timestamp, issuer internal timing |
| Policy Compliance | Agent is operating within all mandate bounds | Full policy details, period totals, other transactions |
| Trust Tier | Agent trust_tier >= merchant's minimum requirement | Exact tier value, issuer identity, attestation details |

### 6.4 ZK Circuit Specification (Section 35)

```
ZK_CIRCUIT verify_payment(private_inputs, public_inputs) -> proof:

  // Private inputs (known only to issuer/agent)
  private:
    mandate: SpendingMandate      // full mandate with all fields
    commitment: FundingCommitment // vault details
    cell: FundingCell             // UTXO being spent
    agent_cert: AgentCertificate  // full certificate
    issuer_key: PublicKey         // for signature verification in-circuit

  // Public inputs (visible to merchant verifier)
  public:
    payment_amount: uint256       // exact amount
    merchant_id: string           // bound merchant
    session_hash: bytes32         // anti-relay binding
    payment_nonce: bytes32        // uniqueness
    expiry: uint64                // validity window
    issuer_pubkey_hash: bytes32   // issuer identity (hashed)
    min_trust_tier: uint8         // merchant requirement

  // Constraints (what the circuit proves)
  ASSERT verify_ed25519(mandate.signature, issuer_key)
  ASSERT verify_ed25519(agent_cert.signature, issuer_key)
  ASSERT agent_cert.trust_tier >= min_trust_tier
  ASSERT contains(mandate.merchant_scope, merchant_id)
  ASSERT payment_amount <= mandate.max_amount_per_tx
  ASSERT cell.denomination >= payment_amount
  ASSERT cell.state == AVAILABLE
  ASSERT current_time < expiry
  ASSERT hash(issuer_key) == issuer_pubkey_hash
  ASSERT session_hash == expected_session_hash

  RETURN proof  // ~128 bytes for Groth16
```

**Implementation path:** Groth16 (fast verification ~10ms, requires trusted setup per circuit) or Plonk (universal setup, slightly larger proofs). Circuit complexity for v1 claims: ~50K constraints. ZK proof generation offloaded to issuer (not agent -- agents are lightweight). Libraries: circom + snarkjs (JS), arkworks (Rust), gnark (Go).

### 6.5 Privacy Tiers (Section 36)

| Tier | When to Use | Verification Overhead | What Merchant Sees | Recommended For |
|------|------------|----------------------|-------------------|-----------------|
| Transparent | Low-value, low-sensitivity | ~0ms (no ZK) | Everything in cleartext | Micropayments (< $1), public API access |
| Hybrid | Medium sensitivity | ~5ms | Amount + merchant binding in cleartext; identity/policy via ZK | Standard SaaS purchases ($1-$500) |
| Full ZK | High sensitivity, enterprise B2B | ~50-200ms | Only: amount, nonce, expiry, proof | Enterprise procurement, competitive contexts ($500+) |

---

## 7. Part VII -- FX Bridge & Liquidity Routing

### 7.1 Cross-Currency Settlement (Section 38-39)

Agent commerce is inherently global. FX conversion happens transparently within the settlement flow, respecting the mandate's slippage tolerance.

**FX Settlement Flow:**

1. Payment Object: source_currency: USDC (from mandate funding), target_currency: EUR (merchant requires), exact_amount: 85.00 EUR
2. Liquidity Router queries providers (parallel):
   - a) Internal liquidity pool: pre-funded USDC/EUR reserve
   - b) On-chain DEX (Uniswap on Base): USDC -> EURC
   - c) Off-chain FX API (Bridge.xyz): USDC -> EUR fiat
   - d) Offramp aggregator (Onramper): USDC -> EUR bank transfer
3. Router selects best rate within `mandate.fx_policy.max_slippage_bps`
4. Atomic execution: USDC debited from FundingCell, FX conversion executed, EUR delivered to merchant
5. Settlement Receipt records: actual FX rate, fees, provider, slippage

### 7.2 FXPolicy (Mandate Field)

```json
{
  "fx_policy": {
    "max_slippage_bps": 50,           // 0.50% max acceptable slippage
    "preferred_fx_providers": [        // ordered preference
      "internal_pool",
      "bridge_xyz",
      "uniswap_base"
    ],
    "allow_onchain_swap": true,        // permit on-chain DEX routing
    "fx_rate_source": "market",        // market | fixed | oracle
    "reject_above_fee_bps": 100        // reject if total fee > 1%
  }
}
```

### 7.3 Bridge Provider Adapters (Section 41)

| Provider | Type | Supported Pairs | Settlement Speed | Integration |
|----------|------|----------------|-----------------|-------------|
| Internal pool | Pre-funded reserve | Any pair with liquidity | Instant | Internal ledger |
| Bridge.xyz | Fiat offramp | USDC -> USD/EUR/GBP fiat | Minutes | REST API |
| Onramper | Aggregator | Multi-fiat <-> multi-crypto | Minutes | REST API |
| Uniswap (Base) | On-chain DEX | USDC <-> EURC, USDC <-> DAI | Seconds | Smart contract |
| Curve (Ethereum) | On-chain DEX | Stablecoin pairs | Seconds | Smart contract |
| Wise / Nium | Fiat-to-fiat | 50+ currency pairs | Hours | REST API |

---

## 8. Part VIII -- Technical Architecture

### 8.1 System Layers (Section 43)

Hexagonal (ports & adapters) architecture:

| Layer | Responsibility | Key Components |
|-------|---------------|----------------|
| Protocol Core | Object creation, validation, state transitions | Mandate Engine, Token Minter, State Machine, Policy Evaluator |
| Identity | Agent registration, certificates, trust tiers | Certificate Authority, Trust Registry, KMS, Revocation Broadcaster |
| Funding | UTXO cell management, reserve locking | Cell Manager, Vault Adapters, Split/Merge Engine, Lock Ledger |
| Settlement | Rail selection, FX routing, clearing | Liquidity Router, Rail Adapters, FX Engine, Receipt Generator |
| Escrow | Timelock holds, delivery confirmation | Escrow Manager, Timelock Service, Auto-Release Scheduler |
| Governance | Disputes, arbitration, audit, compliance | Dispute Engine, Arbitration Node, Audit Logger, Evidence Store |
| Privacy | ZK proof generation and verification | Circuit Compiler, Proof Generator (issuer-side), Verification SDK (merchant-side) |

### 8.2 Component Topology (Section 44)

**Issuer Node (Most Critical):** The central trust anchor. Runs: Mandate Engine, Cell Manager, Token Minter, Funding Manager, Revocation Broadcaster, Clearance Lock Manager, Policy Evaluator.

**Merchant Verification SDK:** Lightweight client library. Handles: signature verification (JWS/COSE), agent certificate chain validation, payment object claim checking (transparent, hybrid, or ZKP), nonce/expiry verification, session_hash recomputation and matching, bloom filter check for revocation, merchant binding confirmation.

**Agent SDK:** Client library for agent developers. Handles: mandate request/approval flow, payment object acquisition from issuer, merchant presentation (with session_hash), retry logic, receipt collection, fulfillment ACK, usage report co-signing, dispute filing.

**Settlement Facilitator / Liquidity Router:** Processes verified payment objects: obtains clearance lock, selects optimal rail, executes FX conversion, manages escrow lifecycle, executes settlement, emits receipts, handles rail-specific error recovery.

### 8.3 Recommended Tech Stack (Section 45)

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Protocol Core / Issuer | Go (primary) or Rust | Performance, type safety, concurrency |
| API Gateway | gRPC (inter-service) + REST/OpenAPI 3.1 (external) | gRPC for performance; REST for accessibility |
| Cryptography | Ed25519 (JWS RFC 7515) + ECDSA P-256 (HSM) + COSE (RFC 9052) | Ed25519 for speed; P-256 for HSM compat |
| Key Management | HashiCorp Vault / AWS KMS / Google Cloud KMS | HSM-backed storage, auto-rotation |
| Primary Database | PostgreSQL 16+ (JSONB) | ACID, FOR UPDATE SKIP LOCKED for cells |
| Event Store / Audit | Apache Kafka or NATS JetStream | Append-only event log, exactly-once delivery |
| Cache / Session | Redis 7+ (with Streams) | Nonce dedup, revocation bloom filter, rate limiting |
| ZK Proofs | gnark (Go) / arkworks (Rust) / circom+snarkjs (JS) | Groth16/Plonk proof generation |

### 8.4 Data Model & Storage (Section 46)

**Core tables:**
- `agent_certificates` (id PK, issuer_id, principal_id, public_key, trust_tier, status, ...)
- `spending_mandates` (id PK, principal_id, agent_id, policy JSONB, fx_policy JSONB, ...)
- `funding_commitments` (id PK, mandate_id FK, source_type, total_committed, cell_strategy, ...)
- `funding_cells` (id PK, commitment_id FK, mandate_id FK, denomination, state, claimed_by, ...)
- `payment_objects` (id PK, mandate_id FK, cell_ids JSONB, merchant_id, amount, state, ...)
- `settlement_receipts` (id PK, payment_object_id FK, rail, tx_ref, settled_amount, fx_quote_id, ...)
- `escrow_holds` (id PK, payment_object_id FK, held_amount, state, release_condition JSONB, ...)
- `fx_quotes` (id PK, source_currency, target_currency, rate, provider, slippage_bps, ...)

**Security & audit tables:**
- `state_transitions` (id PK, object_type, object_id, from_state, to_state, timestamp, actor)
- `clearance_locks` (cell_id PK, rail, facilitator_id, locked_at, expires_at)
- `revocation_registry` (handle PK, object_type, object_id, revoked_at, reason)
- `nonce_registry` (nonce PK, object_type, created_at, expires_at) -- with TTL
- `dispute_cases` (id PK, escrow_id FK, reason_code, evidence JSONB, ruling, ...)

**Critical indexes:**
```sql
CREATE INDEX idx_cells_available ON funding_cells(mandate_id, state, denomination)
  WHERE state = 'AVAILABLE';  -- critical for cell claim performance
CREATE INDEX idx_po_inflight ON payment_objects(mandate_id, state)
  WHERE state IN ('ISSUED','PRESENTED','VERIFIED','LOCKED','ESCROWED','SETTLING');
```

### 8.5 API Surface (Section 47)

| API | Consumers | Key Endpoints |
|-----|----------|---------------|
| Issuer API | Agents, Principals | POST /mandates, POST /payment-objects, GET /mandates/{id}, DELETE /mandates/{id} (revoke), POST /commitments/split |
| Merchant Verification API | Merchants | POST /verify (cleartext or ZKP), POST /settle (request settlement), POST /fulfill (ACK delivery) |
| Settlement Facilitator API | Issuer, Merchant | POST /clearance-lock, POST /route, POST /execute, POST /reverse |
| Escrow API | System, Agents | POST /escrow/confirm (agent ACK), GET /escrow/{id}/status, POST /escrow/dispute |
| Revocation Stream | Merchants | WebSocket /ws/revocations/{issuer_id} (real-time bloom filter updates) |
| Subscription API | Agents, Principals | POST /subscriptions, POST /subscriptions/{id}/pause, DELETE /subscriptions/{id} |

All APIs use mutual TLS. Auth via signed JWTs with short expiry (5 min). Rate limiting per agent certificate and per merchant.

### 8.6 Performance & Scaling Targets (Section 48)

| Metric | v1.0 Target | v1.1 Target (Internal) |
|--------|------------|----------------------|
| Payment object minting | < 50ms p99 | < 50ms p99 |
| Merchant verification (transparent) | < 20ms p99 | < 20ms p99 |
| Merchant verification (ZKP) | < 200ms p99 | < 200ms p99 |
| Cell claim (concurrent) | < 10ms p99 | < 10ms p99 |
| Settlement routing | < 100ms p99 | < 5ms p99 (internal) |
| Revocation propagation | < 500ms end-to-end | < 500ms end-to-end |
| Throughput (sustained) | 10,000 tx/sec | 50,000 tx/sec (internal) |
| Nonce deduplication | < 5ms | < 5ms |
| Settlement cost | $0.01 - 2.9% (rail dependent) | ~$0 (internal), basis point fee only |

---

## 9. Part IX -- Dispute & Arbitration Protocol

### 9.1 Escrow-First Settlement (Section 49)

Transactions above a configurable threshold route through escrow by default. Below threshold, instant settlement applies.

> Payment goes to escrow, not to merchant. Merchant sees proof of locked funds. Merchant delivers. Agent confirms. Escrow releases. If dispute: arbitration decides.

### 9.2 Dispute Protocol & Evidence Model (Section 50)

| Phase | Duration | Actor | Action |
|-------|----------|-------|--------|
| 1. Escrow Hold | Per escrow_profile | System | Funds locked in escrow after merchant verification |
| 2. Delivery | Within timeout | Merchant | Delivers service/data/goods; submits signed proof-of-delivery |
| 3. Confirmation | Within timeout | Agent | Confirms receipt -> FULFILLED. If no ACK: auto-dispute (T11) |
| 4. Dispute Init | Within dispute_window | Agent or Principal | Files dispute with evidence_hash + reason_code |
| 5. Evidence | evidence_deadline (3d default) | Both parties | Merchant: delivery proof, logs. Agent: failure proof, error logs |
| 6. Arbitration | 5 business days | Arbitration Node | Reviews evidence, applies ruling rules, issues binding decision |
| 7. Resolution | Immediate | System | Escrow to winner: RESOLVED_REFUND / RESOLVED_RELEASE / RESOLVED_SPLIT |

**Reason codes available:** SERVICE_NOT_DELIVERED, WRONG_ITEM, QUALITY_ISSUE, UNAUTHORIZED_CHARGE, DUPLICATE_CHARGE, AMOUNT_MISMATCH

### 9.3 Dispute State Machine (Section 52)

| State | Description | Transitions |
|-------|-------------|-------------|
| HELD | Funds in escrow, delivery pending | CONFIRMING, DISPUTING, AUTO_RELEASING |
| CONFIRMING | Agent reviewing delivery | RELEASED, DISPUTING |
| AUTO_RELEASING | Timelock expired, no dispute filed | RELEASED |
| RELEASED | Escrow released to merchant | DISPUTING (within dispute_window), SETTLING |
| DISPUTING | Dispute filed, evidence collection open | ARBITRATING |
| ARBITRATING | Arbitration node reviewing | RESOLVED_REFUND, RESOLVED_RELEASE, RESOLVED_SPLIT |
| RESOLVED_REFUND | Full refund to principal | Terminal |
| RESOLVED_RELEASE | Funds to merchant (dispute rejected) | Terminal |
| RESOLVED_SPLIT | Partial refund + partial release | Terminal |

### 9.4 Integration with Card & Stablecoin Rails (Section 53)

- **Card rail:** Escrow = auth-hold / delayed capture. If dispute: standard chargeback flow as fallback.
- **Stablecoin rail:** Escrow = smart contract (timelock + multi-sig release) or issuer-custodied hold. On-chain proof of escrow visible to merchant.
- **Bank rail:** Escrow = issuer-held reserve with delayed ACH/RTP push. Release triggers push to merchant's bank account.

---

## 10. v1.1 Addendum -- Internal Ledger

### 10.1 The Shift

v1.0 designed Sardis as an authorization and lifecycle protocol that settles over external rails (x402, Stripe, ACH). **v1.1 makes a fundamental architectural shift: the Sardis internal ledger becomes the primary settlement rail.** External rails are demoted to on-ramp (money entering Sardis) and off-ramp (money leaving Sardis) functions.

This is the PayPal/Alipay/M-Pesa/WeChat Pay model applied to machine commerce.

**Three strategic consequences:**
1. Settlement speed drops from seconds/days to **~1 millisecond** (single atomic PostgreSQL transaction)
2. Settlement cost drops to **near zero**, making sub-cent micropayments viable
3. **Network effect becomes the primary moat** -- every new merchant makes the system faster and cheaper for every agent

### 10.2 How Money Moves

**Stage 1: On-Ramp** -- Principal deposits funds via bank transfer, card deposit, stablecoin transfer (USDC on Base/Polygon), or credit facility. System creates OnRampDeposit record and credits the principal's vault balance. FundingCells spawned from this balance.

**Stage 2: Internal Circulation** -- Settlement is a single atomic database transaction: payer's FundingCell transitions to SPENT, merchant's MerchantAccount balance is credited. A LedgerEntry is created as the immutable record. **No external API call, no network latency, no third-party fee.**

**Stage 3: Off-Ramp** -- When a merchant/principal wants to withdraw, Sardis routes through the optimal channel: bank transfer (ACH/wire), stablecoin withdrawal (USDC to external wallet), or card payout. **This is the only point where external rail fees apply.**

### 10.3 New Protocol Objects (v1.1)

**MerchantAccount:** Sardis-native balance account for merchants. Fields include `account_id`, `merchant_id`, `display_name`, `balance`, `currency`, `status`, `kyb_status`, `off_ramp_config`, `auto_withdraw_threshold`.

**LedgerEntry:** The immutable double-entry record. **This is the canonical source of truth -- not the payment object state, not the cell state.** If there is ever a discrepancy, the ledger wins. Fields include `entry_id`, `debit_account`, `credit_account`, `amount`, `currency`, `payment_object_id`, `entry_type` (settlement/escrow_hold/escrow_release/refund/off_ramp/on_ramp/fee), `previous_entry_hash` (hash chain per account).

**Double-entry invariant:** The sum of all debits must equal the sum of all credits at all times. A nightly reconciliation job verifies this. If violated, all settlements are paused and an alert fires.

**OnRampDeposit:** Tracks money entering Sardis from external sources. Fields include `deposit_id`, `principal_id`, `source_type` (bank_transfer/card_deposit/stablecoin_transfer/credit_facility), `amount`, `cells_created`, `status`.

**OffRampWithdrawal:** Tracks money leaving Sardis. Fields include `withdrawal_id`, `source_account`, `destination_type` (bank_transfer/stablecoin_withdrawal/card_payout/wire), `amount`, `fee`, `status`, `initiated_by` (merchant_manual/auto_threshold/principal_manual).

### 10.4 Settlement Routing Decision Tree

| Priority | Condition | Settlement Path | Latency | Fee |
|----------|-----------|----------------|---------|-----|
| 1 (Primary) | Merchant has Sardis account | Internal ledger transfer | ~1ms | ~0.1% |
| 2 | Merchant accepts stablecoin, no Sardis account | x402 / on-chain settlement | 2-30 seconds | ~0.3% + gas |
| 3 | Merchant accepts card payments | Card rail via Stripe/Adyen/Lithic | T+1 to T+2 days | ~2.9% + $0.30 |
| 4 | Merchant accepts bank transfer | ACH / RTP / wire | Minutes to days | ~$0.25-$25 |

### 10.5 Revenue Model (v1.1)

| Revenue Stream | Rate | Description | Incentive Created |
|---------------|------|-------------|-------------------|
| Internal settlement fee | ~0.1% | Charged on every Sardis-to-Sardis transaction | Still 30x cheaper than card -- agents auto-prefer this path |
| External settlement fee | ~0.5% + pass-through | Charged when merchant is NOT on Sardis | Incentivizes merchants to join Sardis (saves 80%+ vs card) |
| Off-ramp fee | Flat ~$0.25 per withdrawal | Charged when money exits Sardis to bank/wallet | Incentivizes keeping balance inside the ecosystem |
| Float / treasury yield | Market rate | Interest earned on aggregate Sardis-held balances | Grows with total deposits |
| Premium features | Subscription | ZKP privacy, advanced analytics, priority settlement, higher limits | Enterprise upsell |

### 10.6 Regulatory Considerations

Holding customer balances and facilitating internal transfers makes Sardis an **e-money institution or money transmitter** depending on jurisdiction. Same regulatory category as PayPal, Square Cash, and Venmo.

**Phase 0-3 strategy:** Operate under a Banking-as-a-Service (BaaS) partner (Unit, Treasury Prime, Modulr). BaaS partner holds the regulatory licenses. This is how Stripe started (Wells Fargo's acquiring license).

---

## 11. Appendix A -- Complete Object Registry

| # | Object | Type | Key Fields |
|---|--------|------|------------|
| 1 | AgentCertificate | Core | agent_id, issuer_id, principal_id, trust_tier, public_key |
| 2 | SpendingMandate | Core | mandate_id, merchant_scope, max_amounts, in_flight_limit, fx_policy |
| 3 | FundingCommitment | Core | commitment_id, total_committed, cell_strategy, refund_destination |
| 4 | FundingCell | Core (UTXO) | cell_id, denomination, state, claimed_by, parent_cell_id |
| 5 | OneTimePaymentObject | Core | po_id, cell_ids, session_hash, privacy_mode, escrow_required |
| 6 | SettlementReceipt | Core | receipt_id, settled_amount, fx_quote_id, fulfillment_status |
| 7 | EscrowHold | Core | escrow_id, held_amount, release_condition, timeout, dispute_window |
| 8 | FXQuote | Core | fx_quote_id, rate, slippage_bps, provider, validity window |
| 9 | SubscriptionMandate | Recurring | subscription_id, pricing_model, adjustment_rule, cumulative caps |
| 10 | ChargeIntent | Recurring | charge_intent_id, sequence_no, reason, usage_report, countersignature |
| 11 | UsageReport | Recurring | report_id, line_items, merchant_sig, agent_countersig, evidence_hash |
| 12 | CreditFacility | BNPL | facility_id, credit_limit, utilized, installment_count |
| 13 | DisputeCase | Dispute | dispute_id, reason_code, evidence, ruling, arbiter_signature |
| 14 | ClearanceLock | Security | cell_id, rail, facilitator_id, locked_at, expires_at |
| 15 | ZKPaymentProof | Privacy | proof_bytes, public_inputs, circuit_id, verification_key_id |
| 16 | MerchantAccount | v1.1 | account_id, merchant_id, balance, kyb_status, off_ramp_config |
| 17 | LedgerEntry | v1.1 | entry_id, debit_account, credit_account, amount, previous_entry_hash |
| 18 | OnRampDeposit | v1.1 | deposit_id, source_type, amount, cells_created, status |
| 19 | OffRampWithdrawal | v1.1 | withdrawal_id, destination_type, amount, fee, status |

---

## 12. Hackathon Implementation Gap Analysis

### Already Implemented in Hackathon Code

| Protocol Concept | Implementation | File(s) |
|-----------------|---------------|---------|
| Spending Mandate (core fields) | `MandateNode` dataclass with budget, scope, delegation | `src/types.py`, `src/mandates/mandate_store.py` |
| Mandate delegation trees with scope narrowing | `MandateStore.delegate()` with subset enforcement | `src/mandates/mandate_store.py` |
| In-flight limit (T4: anti-shadow-lock) | `in_flight_limit` field on MandateNode, `in_flight_count` tracking | `src/types.py` line 133-134 |
| Session hash binding (T3: anti-relay) | `session_hash` field on PaymentIntentEvent | `src/types.py` line 66 |
| 12-check policy engine | `evaluate_policy()` with per-check audit trail | `src/policy.py` |
| 10-check governance engine | `GovernanceEngine.evaluate()` with parent chain validation | `src/governance/engine.py` |
| Hash chain for audit trail | `compute_hash()` on PaymentIntentEvent with `prev_hash` linking | `src/types.py` line 81-86 |
| Deduplication / replay protection | `DedupStore` with idempotency keys, nonces, fingerprints | `src/security/dedup.py` |
| Freeze/resume mandate actions | `freeze()`, `freeze_children()`, `freeze_tree()`, `resume()` | `src/mandates/mandate_store.py` |
| Spend propagation up delegation chain | `record_spend()` walks up parent chain | `src/mandates/mandate_store.py` |
| Risk scoring engine (ML-based) | `RiskAssessment` with IsolationForest anomaly detection | `src/types.py`, `src/risk/engine.py` |
| AML/Sanctions screening | Address risk and sanctions checking | `src/compliance/` |
| Audit evidence packs | `AuditEvidencePack` dataclass with full session evidence | `src/types.py` |

### NOT Implemented -- High-Impact Additions for Demo

| Protocol Concept | Effort | Impact on Demo | Why It Impresses |
|-----------------|--------|---------------|------------------|
| **UTXO FundingCells with FOR UPDATE SKIP LOCKED** | Medium (2-3h) | CRITICAL | Shows you understand concurrency at a database primitive level. "We don't use balance counters, we use UTXO cells with Postgres skip-locked -- the same structural guarantee Bitcoin uses, but without consensus overhead." |
| **One-Time Payment Object minting** | Medium (2h) | HIGH | The core protocol innovation. Show the full lifecycle: mandate -> cell claim -> split -> session_hash binding -> PO mint -> verification. |
| **Settlement Clearance Lock** | Low (1h) | HIGH | Extremely simple to implement (one DB table + atomic check), but shows deep protocol thinking. "Double-settlement is structurally impossible." |
| **22-state state machine visualization** | Low (1h) | HIGH | A visual state machine diagram in the dashboard showing the current state of each payment object. Judges love seeing state machines. |
| **Revocation Bloom Filter (WebSocket)** | Medium (2h) | MEDIUM-HIGH | Shows real-time security. "Revocation propagates in < 500ms via bloom filter broadcast, not polling." |
| **ZKP hybrid mode (mock proof)** | Low (1h) | HIGH | Even a mock proof with the circuit spec showing what's public vs private is extremely impressive. "The merchant verifies the payment is valid without seeing the mandate scope, principal identity, or budget." |
| **Internal ledger settlement (~1ms path)** | Medium (2h) | HIGH | "When both parties are on Sardis, settlement is a single SERIALIZABLE PostgreSQL transaction. ~1ms, zero external dependencies, zero gas." |
| **Escrow flow with timelock** | Medium (2-3h) | MEDIUM | Shows dispute resolution is protocol-native, not an afterthought. |

### NOT Implemented -- Lower Priority

| Protocol Concept | Why Deprioritize for Demo |
|-----------------|--------------------------|
| Full ZKP with Groth16 circuit | Requires circom/gnark setup, too complex for hackathon timeframe |
| FX Bridge with real provider adapters | FX is a detail, not the core innovation |
| Subscription Mandate with charge trees | Recurring is an extension, not the core protocol |
| BNPL / CreditFacility | Requires credit infra -- Phase 3+ |
| Multi-agent delegation chains | Nice to have but delegation trees already cover this |
| Agent Certificate with real Ed25519 | Simplified signature in hackathon is fine for demo |

---

## 13. Demo Strategy for Paradigm

### What to Show (Priority Order)

**1. "The Payment Object Is Not a Credential"** (30 seconds)
Show a One-Time Payment Object being minted, used, and burned. Contrast with: "Every other system gives agents reusable credentials. We mint single-use payment capabilities. Like a cashier's check vs a credit card."

**2. "UTXO Cells Prevent Double-Spending Without Consensus"** (60 seconds)
Demo: Fire 10 concurrent payment requests against the same mandate. Show each one claiming a different FundingCell via FOR UPDATE SKIP LOCKED. Show the split (change output). "This is Bitcoin's model without the blockchain -- structural impossibility of double-spending at the database level."

**3. "11 Attack Vectors, 11 Protocol-Level Mitigations"** (60 seconds)
Walk through the threat table. Highlight T3 (session-bound anti-relay), T4 (in-flight limit anti-shadow-lock), T8 (settlement clearance lock). "We didn't invent security mitigations after building the system. The mitigations ARE the system."

**4. "22-State Lifecycle"** (30 seconds)
Show the state machine diagram. "This is the most comprehensive payment state machine designed for agent commerce. It handles escrow, partial settlement, disputes, FX, and fulfillment acknowledgment."

**5. "~1ms Settlement When Both Parties Are On Sardis"** (30 seconds)
Show internal ledger settlement: single PostgreSQL transaction, cell SPENT, merchant credited, LedgerEntry created. "PayPal's model applied to machine commerce. No gas, no card fees, no latency."

### The Killer Line for Judges

> "Existing protocols solve intent (AP2), identity (TAP), and micro-settlement (x402) separately. We built the execution layer that connects all three -- with UTXO funding, escrow-native disputes, zero-knowledge privacy, and a 22-state lifecycle that no existing standard covers. And when both parties are on Sardis, settlement is a 1-millisecond database transaction."

### SIP Registry Reference (Governance)

Show the SIP (Sardis Improvement Proposals) system. 16 SIPs defined, 8 at P0-Critical status. This shows the protocol is designed for evolution, not just a one-off implementation.

| SIP | Title | Priority |
|-----|-------|----------|
| SIP-001 | UTXO-Based FundingCells | P0 -- Critical |
| SIP-002 | Escrow-Native Dispute Resolution | P0 -- Critical |
| SIP-003 | Session-Bound Payment Objects (Anti-Relay) | P0 -- Critical |
| SIP-004 | In-Flight Limit (Anti-Shadow-Lock) | P0 -- Critical |
| SIP-005 | Revocation Bloom Filter Broadcast | P0 -- Critical |
| SIP-006 | Agent Countersignature on Usage Reports | P0 -- Critical |
| SIP-007 | Settlement Clearance Lock (Anti-Double-Settlement) | P0 -- Critical |
| SIP-008 | Permanent Refund Destination (Master Treasury) | P0 -- Critical |
| SIP-009 | Fulfillment ACK State | P1 -- High |
| SIP-010 | FX Policy & Liquidity Router | P1 -- High |
| SIP-011 | ZKP Privacy Tiers (Transparent/Hybrid/Full) | P2 -- Medium |
| SIP-012 | BNPL / CreditFacility | P3 -- Later |
| SIP-013 | Multi-Agent Delegation Chains | P3 -- Later |
| SIP-014 | Conditional Payment Objects (Oracle-gated) | P3 -- Later |
| SIP-015 | Batch Micropayment Objects | P3 -- Later |
| SIP-016 | Cross-Merchant Session Mandates | P3 -- Later |
