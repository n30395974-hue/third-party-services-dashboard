# Room availability shows stale data after 10 minutes

The occupancy feed is cached forever right now, so rooms show "free" after someone has walked in. We should expire the cache every 60s.

Joe Smith hit this while testing in the library on Thursday.

## Comments

_No comments._
