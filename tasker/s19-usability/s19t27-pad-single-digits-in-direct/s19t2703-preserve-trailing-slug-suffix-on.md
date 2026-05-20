---
id: s19t2703
slug: preserve-trailing-slug-suffix-on
status: pending
---

# Preserve trailing -slug suffix on direct refs

Make `_normalize_direct_ref` split the input into the `s<digits>(t<digits>)?` prefix and an optional `-slug` tail, normalize the prefix, and re-attach the slug. Test that `s1-foo` resolves the same as `s01-foo`.
