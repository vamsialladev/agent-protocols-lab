# Red team

Every attack below is a pytest test that runs in CI on every push (`make test`). They're protocol attacks, not
prompt attacks: only one demo (Agora) calls a model, and only when you run it live. The prompt-injection corpus for
the hotel apps lives in [hotel-ai-platform](https://github.com/vamsialladev/hotel-ai-platform/blob/main/docs/RED_TEAM.md).

| Attack | Demo | What stops it | Test |
|---|---|---|---|
| Call another agent with a wrong or missing token | A2A, ACP | Bearer token, constant-time compare | `test_a2a.py::test_a_wrong_token_is_refused`, `test_acp.py::test_a_wrong_token_is_refused` |
| Send a malformed task | A2A | The task fails cleanly, nothing half-done | `test_a2a.py::test_a_bad_request_fails_the_task_cleanly` |
| Reuse an auth header made for another domain | ANP | did:wba header bound to the receiver's domain | `test_anp.py::test_a_header_made_for_another_domain_is_refused` |
| Unknown DID, or a forged DID document | ANP | Key resolved from the DID, signature checked | `test_anp.py::test_unknown_did_and_a_forged_document_are_refused` |
| Replay an old signed message | ANP | Timestamp window | `test_anp.py::test_a_stale_message_is_refused` |
| Overspend, or replay a payment | AP2 | $200 per payment, $300 a day, one use per mandate | `test_ap2.py::test_limits_and_replay_in_one_session` |
| Change the cart after the guest signed it | AP2 | ES256 signature over the cart | `test_ap2.py::test_a_cart_changed_after_signing_is_refused` |
| Pay a merchant the guest didn't approve | AP2 | Merchant must match the intent mandate | `test_ap2.py::test_a_merchant_outside_the_intent_is_refused` |
| Use an expired cart | AP2 | Expiry checked before payment | `test_ap2.py::test_an_expired_cart_is_refused` |
| Sign with another key, or reuse a signature for another payment | AP2 | Key and payment ID bound into the signature | `test_ap2.py::test_a_signature_from_another_key_or_for_another_payment_is_refused` |
| Replay a paid request | x402 (mock) | Voucher used once | `test_x402.py::test_402_then_pay_then_data_and_a_replay_is_refused` |
| Forge a voucher, or use one for another payment | x402 (mock) | HMAC-signed voucher; payee, amount and network must match | `test_x402.py::test_a_forged_or_mismatched_voucher_does_not_settle` |
| Render a component or send an event outside the allowlist | A2UI | Allowlist plus the official validator | `test_a2ui.py::test_components_and_events_outside_the_allowlist_are_refused`, `test_the_official_validator_rejects_a_malformed_allowed_component` |
| Send a broken component tree | A2UI | Tree and protocol checks | `test_a2ui.py::test_tree_problems_and_protocol_problems_are_refused` |
| Call an MCP tool that isn't allowlisted | MCP consumer | Refused before it reaches the server, and audited | `test_mcp_consumer.py::test_only_allowlisted_tools_are_exposed`, `test_refused_calls_never_reach_the_server_and_are_audited` |
| Use a tool your role doesn't have | MCP server | Tools listed per role | `test_mcp_server.py::test_each_role_sees_only_its_tools_and_gets_policy_passages` |
| Send a checkout message in the wrong shape | UCP | Official `ucp-sdk` models | `test_ucp.py::test_every_exchange_conforms_to_the_official_sdk_models`, `test_the_sdk_check_catches_the_spec_only_shapes` |

## What it found

The UCP demo was first written from the spec's examples. Checked against the official SDK, that version failed 6
of 9 checks ([docs/ucp-spec-only-run.md](ucp-spec-only-run.md)); the fixed version conforms 9 of 9
([docs/ucp-sdk-run.md](ucp-sdk-run.md)). The last test above keeps the old shapes and checks the SDK still rejects
them.

## Not covered

No fuzzing, no load, and no prompt-injection cases against the Agora negotiation (it runs live only on request). No
real money, wallets or networks anywhere, so payment attacks are tested against mocks and the official SDKs' models.
