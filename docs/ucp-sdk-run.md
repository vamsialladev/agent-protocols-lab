# Demo 10, SDK-validated version (2026-10-27)
ucp-sdk 0.5.0 from github.com/Universal-Commerce-Protocol/python-sdk, tag v2026-08-25 (commit b6f9b91c). The spec-only version and its SDK check: [ucp-spec-only-run.md](ucp-spec-only-run.md).

`PYTHONPATH=src python -m demos.ucp.demo`:

```
Beach Resort bathrobe x 1: $65.00 (the agent sent price 1; the catalog price was used)
status: completed | order: ord_a85c13e9 http://giftshop.test/orders/ord_a85c13e9
retry with the same Idempotency-Key -> same order: True
validated with ucp-sdk 0.5.0: 9 checks, all conform
   GET /.well-known/ucp response: UcpProfileDocument ok
   POST / request: CheckoutCreateRequest ok
   POST / response: Checkout ok
   PUT /chk_79996edfd2 request: CheckoutUpdateRequest ok
   PUT /chk_79996edfd2 response: Checkout ok
   POST /chk_79996edfd2/complete request: CheckoutCompleteRequest ok
   POST /chk_79996edfd2/complete response: Checkout ok
   POST /chk_79996edfd2/complete request: CheckoutCompleteRequest ok
   POST /chk_79996edfd2/complete response: Checkout ok
```
