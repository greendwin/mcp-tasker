---
id: s19t35
slug: support-tasks-order
status: pending
---

# Support tasks order

We need to be able to override tasks sorting based on implementation oreder.
We can introduce "order" field that *groups* tasks based on this order. In each such group tasks are sorted by their id.
Note: this group behavior is only needed to resolve collisions. But main purpose of these order_id is to manually sort tasks between each other to match implementation order.
