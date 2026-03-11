#!/usr/bin/env python3
"""Simple MQTT load generator for TA-MQTT performance testing.

Designed to run on Ubuntu with Python 3 and paho-mqtt installed.
Example:
  python3 tools/mqtt_load_test.py \
    --host broker.hivemq.com \
    --port 1883 \
    --topic perf/ta-mqtt/test \
    --clients 4 \
    --rate 200 \
    --duration 60 \
    --payload-bytes 512
"""

from __future__ import annotations

import argparse
import json
import signal
import ssl
import string
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

import paho.mqtt.client as mqtt


@dataclass
class PublisherStats:
    attempted: int = 0
    published: int = 0
    publish_errors: int = 0
    connect_errors: int = 0
    disconnects: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)

    def incr(self, field_name: str, amount: int = 1) -> None:
        with self.lock:
            setattr(self, field_name, getattr(self, field_name) + amount)

    def snapshot(self) -> dict[str, int]:
        with self.lock:
            return {
                "attempted": self.attempted,
                "published": self.published,
                "publish_errors": self.publish_errors,
                "connect_errors": self.connect_errors,
                "disconnects": self.disconnects,
            }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MQTT load generator for TA-MQTT")
    parser.add_argument("--host", required=True, help="MQTT broker hostname or IP")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--topic", required=True, help="Target MQTT topic")
    parser.add_argument(
        "--clients", type=int, default=1, help="Number of publisher clients"
    )
    parser.add_argument(
        "--rate",
        type=float,
        default=50.0,
        help="Total target messages/sec across all clients",
    )
    parser.add_argument(
        "--duration", type=int, default=60, help="Test duration in seconds"
    )
    parser.add_argument(
        "--payload-bytes",
        type=int,
        default=256,
        help="Approximate payload size in bytes",
    )
    parser.add_argument(
        "--qos", type=int, choices=(0, 1, 2), default=0, help="MQTT QoS"
    )
    parser.add_argument("--username", default="", help="MQTT username")
    parser.add_argument("--password", default="", help="MQTT password")
    parser.add_argument(
        "--client-prefix", default="ta-mqtt-load", help="MQTT client id prefix"
    )
    parser.add_argument(
        "--message-format",
        choices=("json", "text"),
        default="json",
        help="Payload format",
    )
    parser.add_argument("--tls", action="store_true", help="Enable TLS")
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Disable TLS certificate verification",
    )
    parser.add_argument("--ca-file", default="", help="CA certificate path")
    parser.add_argument("--cert-file", default="", help="Client certificate path")
    parser.add_argument("--key-file", default="", help="Client private key path")
    parser.add_argument(
        "--report-interval",
        type=int,
        default=5,
        help="Progress report interval in seconds",
    )
    return parser


def make_padding(length: int) -> str:
    alphabet = string.ascii_letters + string.digits
    return (alphabet * ((length // len(alphabet)) + 1))[:length]


def make_payload(
    message_format: str, publisher_id: int, sequence: int, payload_bytes: int
) -> str:
    if message_format == "text":
        prefix = (
            f"publisher={publisher_id} sequence={sequence} sent_ts={time.time():.6f} "
        )
        remaining = max(0, payload_bytes - len(prefix))
        return prefix + make_padding(remaining)

    payload = {
        "publisher_id": publisher_id,
        "sequence": sequence,
        "sent_ts": time.time(),
        "payload": "",
    }
    base = json.dumps(payload, separators=(",", ":"))
    remaining = max(0, payload_bytes - len(base))
    payload["payload"] = make_padding(remaining)
    return json.dumps(payload, separators=(",", ":"))


def configure_tls(client: mqtt.Client, args: argparse.Namespace) -> None:
    if not args.tls:
        return
    context = ssl.create_default_context()
    if args.skip_verify:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    if args.ca_file:
        context.load_verify_locations(cafile=args.ca_file)
    if args.cert_file and args.key_file:
        context.load_cert_chain(certfile=args.cert_file, keyfile=args.key_file)
    client.tls_set_context(context)


def publisher_worker(
    publisher_id: int,
    args: argparse.Namespace,
    stop_event: threading.Event,
    stats: PublisherStats,
) -> None:
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"{args.client_prefix}-{publisher_id}",
        clean_session=True,
    )
    if args.username:
        client.username_pw_set(args.username, args.password or None)
    configure_tls(client, args)

    def on_disconnect(_client, _userdata, _disconnect_flags, reason_code, _properties):
        if reason_code != mqtt.MQTT_ERR_SUCCESS:
            stats.incr("disconnects")

    client.on_disconnect = on_disconnect

    try:
        client.connect(args.host, args.port, keepalive=60)
    except Exception:
        stats.incr("connect_errors")
        return

    client.loop_start()
    per_client_rate = args.rate / max(1, args.clients)
    sleep_interval = 0.0 if per_client_rate <= 0 else 1.0 / per_client_rate
    next_publish = time.monotonic()
    sequence = 0

    try:
        while not stop_event.is_set():
            now = time.monotonic()
            if sleep_interval > 0 and now < next_publish:
                time.sleep(min(next_publish - now, 0.1))
                continue

            payload = make_payload(
                args.message_format, publisher_id, sequence, args.payload_bytes
            )
            stats.incr("attempted")
            try:
                info = client.publish(args.topic, payload=payload, qos=args.qos)
                if info.rc == mqtt.MQTT_ERR_SUCCESS:
                    stats.incr("published")
                else:
                    stats.incr("publish_errors")
            except Exception:
                stats.incr("publish_errors")

            sequence += 1
            if sleep_interval > 0:
                next_publish += sleep_interval
            else:
                next_publish = time.monotonic()
    finally:
        try:
            client.loop_stop()
            client.disconnect()
        except Exception:
            pass


def aggregate_stats(stats_list: list[PublisherStats]) -> dict[str, int]:
    totals = {
        "attempted": 0,
        "published": 0,
        "publish_errors": 0,
        "connect_errors": 0,
        "disconnects": 0,
    }
    for stats in stats_list:
        snap = stats.snapshot()
        for key in totals:
            totals[key] += snap[key]
    return totals


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    stop_event = threading.Event()

    def handle_signal(_signum, _frame):
        stop_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    stats_list = [PublisherStats() for _ in range(args.clients)]
    threads = [
        threading.Thread(
            target=publisher_worker,
            args=(publisher_id, args, stop_event, stats_list[publisher_id]),
            daemon=True,
        )
        for publisher_id in range(args.clients)
    ]

    start_time = time.monotonic()
    for thread in threads:
        thread.start()

    next_report = start_time + args.report_interval
    stop_at = start_time + args.duration
    while not stop_event.is_set() and time.monotonic() < stop_at:
        now = time.monotonic()
        if now >= next_report:
            totals = aggregate_stats(stats_list)
            elapsed = max(now - start_time, 1e-9)
            actual_rate = totals["published"] / elapsed
            print(
                json.dumps(
                    {
                        "elapsed_s": round(elapsed, 2),
                        "attempted": totals["attempted"],
                        "published": totals["published"],
                        "publish_errors": totals["publish_errors"],
                        "connect_errors": totals["connect_errors"],
                        "disconnects": totals["disconnects"],
                        "actual_rate_msgs_per_s": round(actual_rate, 2),
                    }
                ),
                flush=True,
            )
            next_report += args.report_interval
        time.sleep(0.2)

    stop_event.set()
    for thread in threads:
        thread.join(timeout=5)

    totals = aggregate_stats(stats_list)
    elapsed = max(time.monotonic() - start_time, 1e-9)
    actual_rate = totals["published"] / elapsed
    result = {
        "host": args.host,
        "port": args.port,
        "topic": args.topic,
        "clients": args.clients,
        "target_rate_msgs_per_s": args.rate,
        "actual_rate_msgs_per_s": round(actual_rate, 2),
        "duration_s": round(elapsed, 2),
        **totals,
    }
    print(json.dumps(result, indent=2))
    return 0 if totals["connect_errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
