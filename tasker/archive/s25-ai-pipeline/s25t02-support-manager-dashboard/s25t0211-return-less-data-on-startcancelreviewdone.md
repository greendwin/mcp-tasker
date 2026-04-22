---
id: s25t0211
slug: return-less-data-on-startcancelreviewdone
status: done
---

# Return less data on start/cancel/review/done MCP functions -- agent already knows its content

Change `start_task`, `review_task`, `cancel_task`, `finish_task`, and `reset_task` MCP functions to return `TaskPreview` instead of `TaskInfo`. Leave `edit_task` unchanged. No new models needed.
