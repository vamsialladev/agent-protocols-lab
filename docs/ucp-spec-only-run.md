# Demo 10, spec-only version: its own run, then the same traffic validated against the official ucp-sdk
ucp-sdk 0.5.0 from github.com/Universal-Commerce-Protocol/python-sdk, tag v2026-08-25 (commit b6f9b91c), 2026-10-27

## The spec-only demo's own output
```
Beach Resort bathrobe x 1: $65.00 (the agent sent price 1; the catalog price was used)
status: completed | order: {'id': 'ord_5c03025e', 'note': 'Sandbox order: nothing ships, no money moved.'}
retry with the same Idempotency-Key -> same order: True
```

## Every request and response validated with the SDK's models
```
FAIL GET /.well-known/ucp response UcpProfileDocument 2 errors
       ucp.payment_handlers.sandbox_token.[key] - String should match pattern '^[a-z](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9_-]*[a-z0
       ucp.payment_handlers.sandbox_token.0.version - Field required
OK   POST /ucp/v1/checkout-sessions request CheckoutCreateRequest
FAIL POST /ucp/v1/checkout-sessions response Checkout 18 errors
       ucp.PlatformSchema.services - Field required
       ucp.PlatformSchema.payment_handlers.sandbox_token.[key] - String should match pattern '^[a-z](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9_-]*[a-z0
       ucp.PlatformSchema.payment_handlers.sandbox_token.0.version - Field required
       ucp.PlatformSchema.payment_handlers.sandbox_token.0.spec - Field required
       ucp.PlatformSchema.payment_handlers.sandbox_token.0.schema - Field required
       ucp.BusinessSchema.services - Field required
FAIL PUT /ucp/v1/checkout-sessions/chk_f3da37fc5d request CheckoutUpdateRequest 1 errors
       line_items - Field required
FAIL PUT /ucp/v1/checkout-sessions/chk_f3da37fc5d response Checkout 18 errors
       ucp.PlatformSchema.services - Field required
       ucp.PlatformSchema.payment_handlers.sandbox_token.[key] - String should match pattern '^[a-z](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9_-]*[a-z0
       ucp.PlatformSchema.payment_handlers.sandbox_token.0.version - Field required
       ucp.PlatformSchema.payment_handlers.sandbox_token.0.spec - Field required
       ucp.PlatformSchema.payment_handlers.sandbox_token.0.schema - Field required
       ucp.BusinessSchema.services - Field required
OK   POST /ucp/v1/checkout-sessions/chk_f3da37fc5d/complete request CheckoutCompleteRequest
FAIL POST /ucp/v1/checkout-sessions/chk_f3da37fc5d/complete response Checkout 19 errors
       ucp.PlatformSchema.services - Field required
       ucp.PlatformSchema.payment_handlers.sandbox_token.[key] - String should match pattern '^[a-z](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9_-]*[a-z0
       ucp.PlatformSchema.payment_handlers.sandbox_token.0.version - Field required
       ucp.PlatformSchema.payment_handlers.sandbox_token.0.spec - Field required
       ucp.PlatformSchema.payment_handlers.sandbox_token.0.schema - Field required
       ucp.BusinessSchema.services - Field required
OK   POST /ucp/v1/checkout-sessions/chk_f3da37fc5d/complete request CheckoutCompleteRequest
FAIL POST /ucp/v1/checkout-sessions/chk_f3da37fc5d/complete response Checkout 19 errors
       ucp.PlatformSchema.services - Field required
       ucp.PlatformSchema.payment_handlers.sandbox_token.[key] - String should match pattern '^[a-z](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9_-]*[a-z0
       ucp.PlatformSchema.payment_handlers.sandbox_token.0.version - Field required
       ucp.PlatformSchema.payment_handlers.sandbox_token.0.spec - Field required
       ucp.PlatformSchema.payment_handlers.sandbox_token.0.schema - Field required
       ucp.BusinessSchema.services - Field required
```
