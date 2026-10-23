# Tools

## ha_stats.py

Reads long-term statistics (the hourly mean/min/max or state/sum HA keeps forever) over the websocket API,
one month per request, and writes CSV. Use it instead of the History tab's download, which loads everything
into the browser at once and can run HA out of memory on the Green.

Read-only: it only sends `auth`, `recorder/list_statistic_ids` and `recorder/statistics_during_period`.
Python 3 standard library, nothing to install.

Setup: create a long-lived access token in HA (Profile → Security) and save it on your computer:

```
mkdir -p ~/.config/ha-stats && pbpaste > ~/.config/ha-stats/token && chmod 600 ~/.config/ha-stats/token
export HA_URL=http://homeassistant.local:8123   # the default
```

Use:

```
python3 tools/ha_stats.py list temperature
python3 tools/ha_stats.py fetch --start 2024-10-01 --period hour sensor.a sensor.b > stats.csv
```

`--period` is `5minute` (only the last 10 days), `hour`, `day`, `week` or `month`. Times are local.
