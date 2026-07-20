"""
PentraceAI Vulnerable Sandbox
------------------------------
A deliberately vulnerable FastAPI application.
Used as the internal test target for the PentraceAI agent.

Vulnerabilities coded in intentionally:
  - BOLA on /api/users/{user_id}/profile
  - Broken Authentication on /api/admin/reports
  - /api/products/{id} is intentionally SAFE (false positive target)

DO NOT expose this application to the public internet.
"""

from fastapi import FastAPI, Header, HTTPException
from typing import Optional

app = FastAPI(
    title="Vulnerable Sandbox",
    description="Deliberately vulnerable API for PentraceAI testing",
    version="1.0.0",
)

# ── Simulated user database ──────────────────────────────────────────────────

USERS = {
    "1": {"user_id": "1", "email": "alice@example.com", "phone": "9876543210", "name": "Alice"},
    "2": {"user_id": "2", "email": "bob@example.com",   "phone": "9123456789", "name": "Bob"},
    "42": {"user_id": "42", "email": "victim@example.com", "phone": "9000000042", "name": "Victim User"},
}

# Simulated token → user_id mapping
VALID_TOKENS = {
    "token-user-1":  "1",
    "token-user-2":  "2",
    "token-attacker": "1",   # attacker is authenticated as user 1
}

ADMIN_TOKEN = "token-admin-secret"

# ── Health check ─────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "app": "vulnerable-sandbox"}


# ── Finding 1: BOLA — Broken Object Level Authorization ──────────────────────
# Vulnerability: No ownership check. Any authenticated user can access
# any user_id. Should check that token owner == requested user_id.

@app.get("/api/users/{user_id}/profile")
def get_user_profile(
    user_id: str,
    authorization: Optional[str] = Header(None),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = authorization.replace("Bearer ", "")

    if token not in VALID_TOKENS:
        raise HTTPException(status_code=401, detail="Invalid token")

    # ← VULNERABILITY: ownership check is missing
    # Should be: if VALID_TOKENS[token] != user_id: raise 403
    # But we intentionally skip it so any user can access any profile

    user = USERS.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@app.get("/api/users/{user_id}/profile/fixed")
def get_user_profile_fixed(
    user_id: str,
    authorization: Optional[str] = Header(None),
):
    """Same endpoint with the fix applied — used by verification step."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = authorization.replace("Bearer ", "")

    if token not in VALID_TOKENS:
        raise HTTPException(status_code=401, detail="Invalid token")

    # ← FIX APPLIED: ownership check enforced
    if VALID_TOKENS[token] != user_id:
        raise HTTPException(status_code=403, detail="Access denied — you can only access your own profile")

    user = USERS.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


# ── Finding 2: Broken Authentication ─────────────────────────────────────────
# Vulnerability: Admin endpoint accepts any token containing "admin"
# in the string. Trivially bypassable.

@app.get("/api/admin/reports")
def get_admin_reports(
    authorization: Optional[str] = Header(None),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.replace("Bearer ", "")

    # ← VULNERABILITY: weak token check — any token with "admin" passes
    # Should be: if token != ADMIN_TOKEN: raise 403
    if "admin" not in token.lower():
        raise HTTPException(status_code=403, detail="Admin access required")

    return {
        "reports": [
            {"id": "R001", "type": "financial", "data": "Q4 revenue: $2.4M"},
            {"id": "R002", "type": "users",     "data": "Total users: 48,291"},
            {"id": "R003", "type": "security",  "data": "Last breach: never"},
        ]
    }


@app.get("/api/admin/reports/fixed")
def get_admin_reports_fixed(
    authorization: Optional[str] = Header(None),
):
    """Same endpoint with fix applied — used by verification step."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.replace("Bearer ", "")

    # ← FIX APPLIED: exact token match required
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "reports": [
            {"id": "R001", "type": "financial", "data": "Q4 revenue: $2.4M"},
        ]
    }


# ── Finding 3: False Positive Target ─────────────────────────────────────────
# This endpoint returns product data for any product_id.
# A naive scanner flags this as BOLA — but it is intentionally public.
# Product catalog is public information. No auth required by design.

@app.get("/api/products/{product_id}")
def get_product(product_id: str):
    products = {
        "1": {"id": "1", "name": "Widget A", "price": 9.99,  "public": True},
        "2": {"id": "2", "name": "Widget B", "price": 14.99, "public": True},
        "3": {"id": "3", "name": "Widget C", "price": 4.99,  "public": True},
    }
    product = products.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product