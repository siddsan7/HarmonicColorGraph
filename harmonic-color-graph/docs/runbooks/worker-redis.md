# Redis connection for the persistent worker

The worker calls `BRPOP` through `redis-py`, so `REDIS_URL` must be a native
Redis TCP URL (`rediss://` when TLS is required). An HTTPS REST endpoint is
not interchangeable: [Upstash's REST API](https://upstash.com/docs/redis/features/restapi)
does not support blocking list commands. Upstash also offers a
[native Redis TCP protocol](https://upstash.com/docs/redis/overall/compatibility).
Keep credentials in the deployment's private environment store.

One continuously idle worker waits up to 15 seconds per `BRPOP` and samples
queue depth every 30 seconds. Over a 31-day month this budgets 178,560
receives and 89,280 depth samples. Adding one health `PING` every 30 seconds
and a 100,000-command traffic reserve totals 457,120 commands, below the
[current Upstash Free limit of 500,000 monthly commands](https://upstash.com/pricing/redis).
Extra workers, retries, reconnects, and higher traffic consume the reserve;
monitor the provider's actual usage before relying on the free tier.

The API queue client keeps a 3-second socket timeout. The persistent worker
uses a 20-second socket timeout so its 15-second blocking receive can finish.
Provisioning, a real TCP connection/wakeup test, persistent host, and live
queue/recovery verification remain part of H01, A07, and L01 in the
[completion checklist](../m0-m7-completion-checklist.md).
