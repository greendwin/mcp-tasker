---
id: s11t1605
slug: make-reportxxx-methods-jsonoutput-agnostic
status: pending
---

# Make _report_xxx methods json_output agnostic

Make `_report_xxx` methods be `json_output` agnostic so no need to check `if not console.json_output` everywhere. `_report_xxx` method should handle it itself (i.e. raise exception in case of `json_output` flag), so caller site should not care about it.
