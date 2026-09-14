from __future__ import annotations

import json

import pytest

from local_mcp_gateway.errors import BinaryMissingError, PublisherError
from local_mcp_gateway.publishers import REGISTRY, create_publisher
from local_mcp_gateway.publishers.cloudflare import CloudflarePublisher
from local_mcp_gateway.publishers.local import LocalPublisher
from local_mcp_gateway.publishers.ngrok import NgrokPublisher
from local_mcp_gateway.publishers.tailscale import TailscalePublisher
from tests.fakes import FakeRunner


def test_registry_exposes_builtin_publishers() -> None:
    assert set(REGISTRY) == {"local", "tailscale", "cloudflare", "ngrok"}
    for name in REGISTRY:
        mode = "funnel" if name == "tailscale" else None
        assert create_publisher(name, mode=mode, runner=FakeRunner())


def test_local_publisher_returns_listen_url() -> None:
    publisher = LocalPublisher()
    endpoint = publisher.start(listen_host="127.0.0.1", listen_port=8788)
    assert endpoint.url == "http://127.0.0.1:8788"
    assert endpoint.mcp_url("paper") == "http://127.0.0.1:8788/paper/mcp"
    publisher.stop()


def test_local_publisher_maps_wildcard_listen_to_loopback() -> None:
    endpoint = LocalPublisher().start(listen_host="0.0.0.0", listen_port=8788)
    assert endpoint.url == "http://127.0.0.1:8788"


def test_create_publisher_unknown() -> None:
    with pytest.raises(PublisherError, match="unknown publisher"):
        create_publisher("not-a-publisher")


def test_tailscale_funnel_uses_status_dns_name() -> None:
    runner = FakeRunner()
    runner.add_run(
        ["tailscale", "status", "--json"],
        stdout=json.dumps({"Self": {"DNSName": "box.tail123.ts.net."}}),
    )
    publisher = TailscalePublisher(mode="funnel", runner=runner)
    endpoint = publisher.start(listen_host="127.0.0.1", listen_port=8788)
    assert endpoint.url == "https://box.tail123.ts.net"
    assert ["tailscale", "funnel", "--bg", "--https=443", "8788"] in runner.runs
    publisher.stop()
    assert ["tailscale", "funnel", "--https=443", "off"] in runner.runs


def test_tailscale_serve_points_at_loopback() -> None:
    runner = FakeRunner()
    runner.add_run(
        ["tailscale", "status", "--json"],
        stdout=json.dumps({"Self": {"DNSName": "box.tail123.ts.net."}}),
    )
    publisher = TailscalePublisher(mode="serve", runner=runner)
    publisher.start(listen_host="127.0.0.1", listen_port=8788)
    assert ["tailscale", "serve", "--bg", "--https=443", "http://127.0.0.1:8788"] in runner.runs
    publisher.stop()
    assert ["tailscale", "serve", "--https=443", "off"] in runner.runs


def test_tailscale_requires_mode() -> None:
    with pytest.raises(PublisherError, match="mode"):
        TailscalePublisher(mode=None, runner=FakeRunner())


def test_tailscale_missing_binary() -> None:
    runner = FakeRunner()
    runner.missing.add("tailscale")
    publisher = TailscalePublisher(mode="funnel", runner=runner)
    with pytest.raises(BinaryMissingError, match="tailscale"):
        publisher.start(listen_host="127.0.0.1", listen_port=8788)


def test_cloudflare_parses_trycloudflare_url() -> None:
    runner = FakeRunner()
    runner.set_spawn_output("INF |  https://random-words.trycloudflare.com\n")
    publisher = CloudflarePublisher(runner=runner)
    endpoint = publisher.start(listen_host="127.0.0.1", listen_port=8788)
    assert endpoint.url == "https://random-words.trycloudflare.com"
    assert runner.spawns == [["cloudflared", "tunnel", "--url", "http://127.0.0.1:8788"]]
    publisher.stop()
    assert runner.spawned is not None
    assert runner.spawned.terminated is True


def test_cloudflare_missing_binary() -> None:
    runner = FakeRunner()
    runner.missing.add("cloudflared")
    publisher = CloudflarePublisher(runner=runner)
    with pytest.raises(BinaryMissingError, match="cloudflared"):
        publisher.start(listen_host="127.0.0.1", listen_port=8788)


def test_ngrok_parses_json_log_url() -> None:
    runner = FakeRunner()
    runner.set_spawn_output(
        json.dumps({"msg": "started tunnel", "url": "https://abc.ngrok-free.app"}) + "\n"
    )
    publisher = NgrokPublisher(runner=runner)
    endpoint = publisher.start(listen_host="127.0.0.1", listen_port=8788)
    assert endpoint.url == "https://abc.ngrok-free.app"
    assert runner.spawns[0][:3] == ["ngrok", "http", "8788"]
    publisher.stop()
    assert runner.spawned is not None
    assert runner.spawned.terminated is True


def test_ngrok_missing_binary() -> None:
    runner = FakeRunner()
    runner.missing.add("ngrok")
    publisher = NgrokPublisher(runner=runner)
    with pytest.raises(BinaryMissingError, match="ngrok"):
        publisher.start(listen_host="127.0.0.1", listen_port=8788)
