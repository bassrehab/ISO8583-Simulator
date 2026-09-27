"""Tests for framing, the TCP client and the mock host, over real local sockets."""

import asyncio
import json

import pytest

from iso8583sim.core.samples import sample_message
from iso8583sim.core.types import ParseError
from iso8583sim.net import Framing, ISO8583Client, MockHost, Rule, load_rules, response_mti
from iso8583sim.net.framing import swap_tpdu
from iso8583sim.wire import WireFormat

TPDU = bytes.fromhex("6000010002")


def run(coro):
    # subhadipmitra@: Plain asyncio.run keeps the tests free of an async pytest plugin.
    return asyncio.run(coro)


async def with_host(test, rules=None, wire_format=None, framing=None, timeout=1.0):
    """Start a mock host on a free port, run test(client, host), then shut both down."""
    host = MockHost(rules=rules, wire_format=wire_format, framing=framing)
    await host.start("127.0.0.1", 0)
    try:
        async with ISO8583Client(
            "127.0.0.1", host.port, wire_format=wire_format, framing=framing, timeout=timeout
        ) as client:
            return await test(client, host)
    finally:
        await host.stop()


class TestFraming:
    @pytest.mark.parametrize(
        "header,prefix",
        [("2b", b"\x00\x05"), ("4b", b"\x00\x00\x00\x05"), ("2a", b"05"), ("4a", b"0005")],
    )
    def test_headers(self, header, prefix):
        assert Framing(header=header).frame(b"HELLO") == prefix + b"HELLO"

    def test_tpdu_is_counted_in_length(self):
        assert Framing(tpdu=TPDU).frame(b"AB") == b"\x00\x07" + TPDU + b"AB"

    def test_header_includes_self(self):
        assert Framing(header="2b", header_includes_self=True).frame(b"AB") == b"\x00\x04AB"

    def test_split_handles_partial_and_multiple_frames(self):
        framing = Framing(tpdu=TPDU)
        stream = framing.frame(b"ONE") + framing.frame(b"TWO") + framing.frame(b"THREE")[:4]
        frames, rest = framing.split(stream)
        assert frames == [(TPDU, b"ONE"), (TPDU, b"TWO")]
        assert rest == framing.frame(b"THREE")[:4]

    def test_too_long(self):
        with pytest.raises(ValueError, match="too long"):
            Framing(header="2a").frame(b"x" * 100)

    def test_invalid_ascii_header(self):
        with pytest.raises(ParseError):
            Framing(header="4a").split(b"00x5HELLO")

    def test_invalid_options(self):
        with pytest.raises(ValueError):
            Framing(header="3b")
        with pytest.raises(ValueError):
            Framing(tpdu=b"\x60")

    def test_swap_tpdu(self):
        assert swap_tpdu(bytes.fromhex("6000010002")) == bytes.fromhex("6000020001")


class TestRules:
    def test_response_mti(self):
        assert [response_mti(m) for m in ("0100", "0200", "0400", "0800", "0120")] == [
            "0110",
            "0210",
            "0410",
            "0810",
            "0130",
        ]
        with pytest.raises(ValueError):
            response_mti("0110")

    def test_matching(self):
        request = sample_message(amount_minor_units=5000)
        assert Rule(amount_gt=1000).matches(request)
        assert not Rule(amount_lt=1000).matches(request)
        assert Rule(pan_prefix=["4111"]).matches(request)
        assert not Rule(mti=["0200"]).matches(request)
        assert Rule(network="visa").matches(request)
        assert Rule(fields={49: "840"}).matches(request)

    def test_from_dict_and_json_file(self, tmp_path):
        path = tmp_path / "rules.json"
        path.write_text(
            json.dumps({"rules": [{"match": {"amount_gt": 100000, "mti": "0100"}, "respond": "51"}, {"respond": "00"}]})
        )
        rules = load_rules(path)
        assert rules[0].mti == ["0100"] and rules[0].respond == "51"

    def test_yaml_file(self, tmp_path):
        pytest.importorskip("yaml")
        path = tmp_path / "rules.yaml"
        path.write_text("rules:\n  - match: {pan_prefix: '4999'}\n    action: drop\n  - respond: '00'\n")
        assert load_rules(path)[0].action == "drop"

    @pytest.mark.parametrize(
        "entry,message",
        [
            ({"match": {"amount": 5}}, "Unknown rule keys"),
            ({"respond": "5"}, "2 characters"),
            ({"action": "explode"}, "action"),
        ],
    )
    def test_invalid_rules(self, entry, message):
        with pytest.raises(ValueError, match=message):
            Rule.from_dict(entry)


class TestClientAndHost:
    def test_approval(self):
        async def test(client, host):
            response = await client.send(sample_message(stan="000001"))
            assert (response.mti, response.fields[39], response.fields[38]) == ("0110", "00", "A00001")
            assert response.fields[4] == "000000001000"

        run(with_host(test))

    def test_rules_apply_in_order(self):
        rules = [Rule(amount_gt=100000, respond="51"), Rule(pan_prefix=["4000"], respond="05"), Rule()]

        async def test(client, host):
            large = await client.send(sample_message(amount_minor_units=500000, stan="000001"))
            blocked = await client.send(sample_message(pan="4000123412341234", stan="000002"))
            normal = await client.send(sample_message(stan="000003"))
            assert [large.fields[39], blocked.fields[39], normal.fields[39]] == ["51", "05", "00"]
            assert 38 not in large.fields
            assert host.stats.response_codes == {"51": 1, "05": 1, "00": 1}

        run(with_host(test, rules=rules))

    def test_echo(self):
        async def test(client, host):
            response = await client.send(sample_message("echo", stan="000009"))
            assert (response.mti, response.fields[39], response.fields[70]) == ("0810", "00", "301")

        run(with_host(test))

    def test_timeout_on_dropped_request(self):
        async def test(client, host):
            with pytest.raises(TimeoutError, match="000007"):
                await client.send(sample_message(stan="000007"), timeout=0.2)
            assert host.stats.dropped == 1

        run(with_host(test, rules=[Rule(action="drop")]))

    def test_out_of_order_responses(self):
        rules = [Rule(pan_prefix=["4000"], delay_ms=300), Rule()]

        async def test(client, host):
            slow = asyncio.create_task(client.send(sample_message(pan="4000123412341234", stan="000001")))
            await asyncio.sleep(0.05)
            fast = await client.send(sample_message(stan="000002"))
            # subhadipmitra@: The fast response arrives first and must still reach its own
            # caller, which is the point of matching on STAN.
            assert not slow.done()
            assert fast.fields[11] == "000002"
            assert (await slow).fields[11] == "000001"

        run(with_host(test, rules=rules))

    def test_many_concurrent_requests(self):
        async def test(client, host):
            responses = await asyncio.gather(*[client.send(sample_message(stan=f"{i:06d}")) for i in range(1, 201)])
            assert [r.fields[11] for r in responses] == [f"{i:06d}" for i in range(1, 201)]

        run(with_host(test))

    def test_duplicate_stan_is_rejected(self):
        async def test(client, host):
            first = asyncio.create_task(client.send(sample_message(stan="000001")))
            await asyncio.sleep(0.05)
            with pytest.raises(ValueError, match="already waiting"):
                await client.send(sample_message(stan="000001"))
            assert (await first).fields[39] == "00"

        run(with_host(test, rules=[Rule(delay_ms=200)]))

    def test_request_without_stan(self):
        async def test(client, host):
            message = sample_message()
            del message.fields[11]
            with pytest.raises(ValueError, match="STAN"):
                await client.send(message)

        run(with_host(test))

    def test_host_closing_fails_pending_request(self):
        async def test(client, host):
            with pytest.raises(ConnectionError):
                await client.send(sample_message(stan="000001"))

        run(with_host(test, rules=[Rule(action="close")]))

    def test_client_reconnects_after_close(self):
        rules = [Rule(pan_prefix=["4999"], action="close"), Rule()]

        async def test(client, host):
            with pytest.raises(ConnectionError):
                await client.send(sample_message(pan="4999123412341234", stan="000001"))
            response = await client.send(sample_message(stan="000002"))
            assert response.fields[39] == "00"

        run(with_host(test, rules=rules))

    @pytest.mark.parametrize("preset", ["ascii-hex", "ascii-binary", "bcd", "ebcdic"])
    @pytest.mark.parametrize("header", ["2b", "4a"])
    def test_every_format_over_tcp(self, preset, header):
        async def test(client, host):
            response = await client.send(sample_message(stan="000042"))
            assert response.fields[39] == "00"
            assert response.fields[2] == "4111111111111111"

        run(with_host(test, wire_format=WireFormat.preset(preset), framing=Framing(header=header, tpdu=TPDU)))

    def test_connection_refused(self):
        async def test():
            client = ISO8583Client("127.0.0.1", 1, timeout=1)
            with pytest.raises(OSError):
                await client.send(sample_message())

        run(test())


class TestLoad:
    def test_counts_and_codes(self):
        from iso8583sim.net import run_load

        async def test():
            host = MockHost(rules=[Rule(pan_prefix=["5"], respond="51"), Rule()])
            await host.start("127.0.0.1", 0)
            try:
                return await run_load(
                    lambda: ISO8583Client("127.0.0.1", host.port, timeout=2),
                    count=100,
                    concurrency=10,
                    connections=3,
                    make_message=lambda i: sample_message(
                        pan="5555555555554444" if i % 4 == 0 else None, stan=f"{i + 1:06d}"
                    ),
                )
            finally:
                await host.stop()

        report = run(test())
        assert (report.sent, report.responses, report.timeouts, report.errors) == (100, 100, 0, 0)
        assert report.response_codes == {"00": 75, "51": 25}
        assert report.throughput > 0
        assert report.percentile(50) <= report.percentile(99)

    def test_timeouts_are_counted(self):
        from iso8583sim.net import run_load

        async def test():
            host = MockHost(rules=[Rule(action="drop")])
            await host.start("127.0.0.1", 0)
            try:
                return await run_load(
                    lambda: ISO8583Client("127.0.0.1", host.port, timeout=0.2), count=5, concurrency=5
                )
            finally:
                await host.stop()

        report = run(test())
        assert (report.responses, report.timeouts) == (0, 5)

    def test_percentile(self):
        from iso8583sim.net import LoadReport

        report = LoadReport(latencies_ms=[float(i) for i in range(1, 101)])
        assert (report.percentile(50), report.percentile(95), report.percentile(100)) == (50.0, 95.0, 100.0)
        assert LoadReport().percentile(99) == 0.0

    def test_invalid_arguments(self):
        from iso8583sim.net import run_load

        with pytest.raises(ValueError):
            run(run_load(lambda: ISO8583Client("127.0.0.1", 1), count=0))
