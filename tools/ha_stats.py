#!/usr/bin/env python3
"""Read long-term statistics from Home Assistant, one month at a time.

Read-only: the only websocket commands this script sends are `auth`,
`recorder/list_statistic_ids` and `recorder/statistics_during_period`.
It has no code that calls services or changes state. Standard library only.

Configuration (environment):
  HA_URL    default http://homeassistant.local:8123
  HA_TOKEN  a long-lived access token (Profile -> Security in HA), or
            put it in ~/.config/ha-stats/token

Examples:
  ha_stats.py list temperature
  ha_stats.py fetch --start 2024-10-01 --period hour sensor.living_temp sensor.attic_temp > out.csv
"""

import argparse
import base64
import csv
import datetime as dt
import json
import os
import socket
import ssl
import struct
import sys
import urllib.parse

TOKEN_FILE = os.path.expanduser("~/.config/ha-stats/token")


class WebSocket:
    """Minimal websocket client (RFC 6455), text messages only."""

    def __init__(self, url):
        u = urllib.parse.urlparse(url)
        secure = u.scheme in ("https", "wss")
        port = u.port or (443 if secure else 80)
        sock = socket.create_connection((u.hostname, port), timeout=120)
        if secure:
            sock = ssl.create_default_context().wrap_socket(sock, server_hostname=u.hostname)
        self.sock = sock
        key = base64.b64encode(os.urandom(16)).decode()
        sock.sendall((
            f"GET /api/websocket HTTP/1.1\r\nHost: {u.hostname}:{port}\r\n"
            "Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        ).encode())
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = sock.recv(1)
            if not chunk:
                raise ConnectionError("connection closed during handshake")
            head += chunk
        if b" 101 " not in head.split(b"\r\n", 1)[0]:
            raise ConnectionError(head.decode(errors="replace").split("\r\n", 1)[0])

    def _recv_exact(self, n):
        buf = bytearray()
        while len(buf) < n:
            chunk = self.sock.recv(min(n - len(buf), 1 << 20))
            if not chunk:
                raise ConnectionError("connection closed")
            buf += chunk
        return bytes(buf)

    def _send_frame(self, opcode, payload):
        header = bytes([0x80 | opcode])
        n = len(payload)
        if n < 126:
            header += bytes([0x80 | n])
        elif n < 1 << 16:
            header += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            header += bytes([0x80 | 127]) + struct.pack(">Q", n)
        mask = os.urandom(4)
        self.sock.sendall(header + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))

    def send(self, obj):
        self._send_frame(0x1, json.dumps(obj).encode())

    def close(self):
        self._send_frame(0x8, struct.pack(">H", 1000))
        self.sock.close()

    def recv(self):
        data = b""
        while True:
            b0, b1 = self._recv_exact(2)
            opcode, n = b0 & 0x0F, b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._recv_exact(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._recv_exact(8))[0]
            payload = self._recv_exact(n)
            if opcode == 0x8:
                raise ConnectionError("server closed the connection")
            if opcode == 0x9:
                self._send_frame(0xA, payload)
                continue
            if opcode in (0x0, 0x1):
                data += payload
                if b0 & 0x80:
                    return json.loads(data)


class HA:
    def __init__(self, url, token):
        self.ws = WebSocket(url)
        self.next_id = 1
        if self.ws.recv().get("type") != "auth_required":
            raise ConnectionError("unexpected greeting")
        self.ws.send({"type": "auth", "access_token": token})
        reply = self.ws.recv()
        if reply.get("type") != "auth_ok":
            raise PermissionError(reply.get("message", "authentication failed"))

    def call(self, msg_type, **params):
        msg_id = self.next_id
        self.next_id += 1
        self.ws.send({"id": msg_id, "type": msg_type, **params})
        while True:
            reply = self.ws.recv()
            if reply.get("id") == msg_id:
                if not reply.get("success"):
                    raise RuntimeError(reply.get("error"))
                return reply["result"]


def connect():
    url = os.environ.get("HA_URL", "http://homeassistant.local:8123")
    token = os.environ.get("HA_TOKEN")
    if not token and os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            token = f.read().strip()
    if not token:
        sys.exit(f"No token: set HA_TOKEN or put it in {TOKEN_FILE}")
    return HA(url, token)


def months(start, end):
    cur = start
    while cur < end:
        nxt = (cur.replace(day=1) + dt.timedelta(days=32)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        yield cur, min(nxt, end)
        cur = nxt


def parse_date(s):
    d = dt.datetime.fromisoformat(s)
    return d if d.tzinfo else d.astimezone()


def cmd_list(ha, args):
    rows = ha.call("recorder/list_statistic_ids")
    w = csv.writer(sys.stdout)
    w.writerow(["statistic_id", "unit", "mean", "sum", "name"])
    for r in sorted(rows, key=lambda r: r["statistic_id"]):
        text = f"{r['statistic_id']} {r.get('name') or ''}".lower()
        if args.filter and args.filter.lower() not in text:
            continue
        w.writerow([r["statistic_id"], r.get("statistics_unit_of_measurement"),
                    r.get("has_mean"), r.get("has_sum"), r.get("name")])


def cmd_fetch(ha, args):
    start = parse_date(args.start)
    end = parse_date(args.end) if args.end else dt.datetime.now().astimezone()
    types = ["mean", "min", "max", "state", "sum"]
    w = csv.writer(sys.stdout)
    w.writerow(["statistic_id", "start"] + types)
    for a, b in months(start, end):
        print(f"{a:%Y-%m}", file=sys.stderr)
        result = ha.call("recorder/statistics_during_period", start_time=a.isoformat(),
                         end_time=b.isoformat(), statistic_ids=args.ids,
                         period=args.period, types=types)
        for sid in args.ids:
            for r in result.get(sid, []):
                t = r["start"]
                t = dt.datetime.fromtimestamp(t / 1000).astimezone() if isinstance(t, (int, float)) else parse_date(t)
                w.writerow([sid, t.isoformat(timespec="minutes")] + [r.get(k) for k in types])
        sys.stdout.flush()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    pl = sub.add_parser("list", help="list sensors that have long-term statistics")
    pl.add_argument("filter", nargs="?", help="only ids or names containing this text")
    pf = sub.add_parser("fetch", help="statistics as CSV on stdout, fetched one month at a time")
    pf.add_argument("--start", required=True, help="e.g. 2024-10-01 (local time)")
    pf.add_argument("--end", help="default: now")
    pf.add_argument("--period", default="hour", choices=["5minute", "hour", "day", "week", "month"])
    pf.add_argument("ids", nargs="+", help="statistic ids, e.g. sensor.living_temperature")
    args = p.parse_args()
    ha = connect()
    {"list": cmd_list, "fetch": cmd_fetch}[args.cmd](ha, args)
    ha.ws.close()


if __name__ == "__main__":
    main()
