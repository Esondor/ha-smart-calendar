# Smart Calendar for Home Assistant

Connects Home Assistant to a self-hosted Smart Calendar server.

- **Smart Calendar in the sidebar**: the tablet view (wall display) as its own page, set up automatically
- **Service** `smart_calendar.event` – e.g. release “Move laundry to dryer” when the washer is done
- **Service** `smart_calendar.complete` – mark a task done
- **Sensors** – next task, open tasks, waiting tasks

## Install

HACS → ⋮ → Custom repositories → `https://github.com/Esondor/ha-smart-calendar` (Integration) → install → restart.
Then Settings → Devices & Services → Add Integration → **Smart Calendar**:

| Field | Value |
|---|---|
| Address | your Smart Calendar URL |
| Access token | Smart Calendar → Settings → Access Tokens |
| Display link | Leave empty: the integration creates it |

The integration registers your Home Assistant addresses with the server so the page may be shown inside Home Assistant (the token must belong to an admin; otherwise add the address in Smart Calendar → Administration → Displays → *Home Assistant address*). The page shows everyone you share projects with. Rename it under the integration's *Configure*.

## Example

```yaml
triggers:
  - trigger: state
    entity_id: sensor.washer_status
    to: finished
actions:
  - action: smart_calendar.event
    data:
      name: washer_done
```

## License

Free for non-commercial use under the [PolyForm Noncommercial License 1.0.0](LICENSE.md), like [Smart Calendar](https://github.com/Esondor/smart-calendar) itself.
