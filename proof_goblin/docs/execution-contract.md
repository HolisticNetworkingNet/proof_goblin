# Execution, Retry, and Duplicate-Cost Contract

Proof Goblin makes provider execution bounded and observable without claiming
provider idempotency. A successful review has one canonical result, but an
ambiguous external failure can still have reached the provider and incurred
cost before the caller receives an error.

## One provider call

`Reviewer.review()` and `review_prepared()` invoke the selected provider once.
For `OpenAIProvider`, that means one call to the OpenAI Python SDK's Responses
API method. The SDK may perform transport retries inside that call. With Proof
Goblin's default client policy, each attempt has a 60-second timeout and the SDK
may retry at most twice, so one adapter call can produce at most three HTTP
attempts when the SDK classifies failures as retryable.

`OpenAIProvider(timeout_seconds=..., max_retries=...)` accepts a positive
timeout and a non-negative retry count. Setting `max_retries=0` disables SDK
transport retries. When a host injects `client=...`, that client's transport,
timeout, and retry configuration is authoritative; Proof Goblin does not mutate
or wrap an injected client.

The timeout bounds how long the client waits for an attempt. It does not prove
that the provider cancelled server-side work, and timeout or connection errors
remain ambiguous for cost and side effects.

## Host and CLI retries

The provider-neutral `Reviewer` performs no additional retry after a provider
method returns or raises. A host that retries calls `review()` again and owns
the total-attempt and elapsed-time budget, backoff, job identity, duplicate
suppression, and the decision to accept possible duplicate provider cost.

Proof Goblin cannot supply an idempotency guarantee when the provider offers no
pre-request idempotency key. A response ID is available only after success and
is useful for correlation, not duplicate prevention.

The CLI performs no outer provider retry. Its cache key identifies the complete
credential-free provider request. Concurrent processes using the same cache
allow only one active request for that key; later processes receive
`ReviewCacheError` rather than contacting the provider.

## Reservation heartbeat and crash recovery

An active CLI reservation updates its private lock file every minute. A lock is
stale only after 15 minutes without a heartbeat. A legitimate long-running
request therefore keeps ownership beyond 15 minutes, while a crashed process's
abandoned lock becomes recoverable after the stale interval.

This is duplicate suppression on an ordinary shared filesystem, not distributed
consensus. A suspended process that cannot run its heartbeat, filesystem or
clock anomalies, manual lock modification, and another process with the same OS
user authority can still defeat the assumption. Hosts needing stronger
coordination should use a durable job store or distributed lease.

`--refresh` and `--force-refresh` deliberately permit another provider call
after a cached success. A failure after a provider response but before the cache
record is stored is also ambiguous: a later invocation can call the provider
again.

## Bounded retry guidance

Choose one layer to own outer retries. Cap both attempts and elapsed time, retry
only classified transient failures, and stop automatic retries after an
ambiguous timeout unless duplicate cost is accepted. Quota errors, refusals,
invalid schemas, invalid output, and local limit failures should not be retried
unchanged.

See {doc}`errors` for exception-specific recovery and {doc}`host-integration`
for the provider-neutral application boundary.
