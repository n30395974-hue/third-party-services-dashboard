# Timer drifts when the tab is in the background

Chrome throttles `setInterval` in background tabs, so a 25-minute session ends up ~27 minutes. Compute remaining time from `Date.now()` instead of counting ticks.

## Comments

_No comments._
