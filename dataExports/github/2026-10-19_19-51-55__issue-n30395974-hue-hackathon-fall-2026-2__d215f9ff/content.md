# Bot crashes when amount has a dollar sign

`/split $20 tacos @joe` throws `NaN`. Need to strip the `$` before parsing. Found by Joe Smith during the demo, very embarrassing.

## Comments

_No comments._
