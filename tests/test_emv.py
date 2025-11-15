# tests/test_emv.py
"""Tests for the EMV TLV parsing module."""

from iso8583sim.core.emv import (
    EMV_TAGS,
    build_emv_data,
    explain_cid,
    explain_tvr,
    get_tag_name,
    parse_emv_data,
)


class TestParseEmvData:
    """Tests for parse_emv_data function."""

    def test_parse_simple_tag(self):
        """Test parsing a single EMV tag."""
        data = "9F2608AABBCCDD11223344"
        result = parse_emv_data(data)
        assert "9F26" in result
        assert result["9F26"] == "AABBCCDD11223344"

    def test_parse_single_byte_tag(self):
        """Test parsing single-byte tag."""
        data = "9A03251215"  # Transaction Date
        result = parse_emv_data(data)
        assert "9A" in result
        assert result["9A"] == "251215"

    def test_parse_multiple_tags(self):
        """Test parsing multiple EMV tags."""
        data = "9F2608AABBCCDD112233449F270180"
        result = parse_emv_data(data)
        assert "9F26" in result
        assert "9F27" in result
        assert result["9F26"] == "AABBCCDD11223344"
        assert result["9F27"] == "80"

    def test_parse_two_byte_length(self):
        """Test parsing with 2-byte length encoding (81xx)."""
        # Tag with length > 127 bytes (using 81 prefix)
        value = "AA" * 130  # 130 bytes
        data = f"9F1081{130:02X}{value}"
        result = parse_emv_data(data)
        assert "9F10" in result
        assert result["9F10"] == value

    def test_parse_three_byte_length(self):
        """Test parsing with 3-byte length encoding (82xxxx)."""
        # Tag with length > 255 bytes (using 82 prefix)
        value = "BB" * 300  # 300 bytes
        data = f"9F1082{300:04X}{value}"
        result = parse_emv_data(data)
        assert "9F10" in result
        assert result["9F10"] == value

    def test_parse_empty_data(self):
        """Test parsing empty data."""
        result = parse_emv_data("")
        assert result == {}

    def test_parse_case_insensitive(self):
        """Test that parsing is case insensitive."""
        data_lower = "9f2608aabbccdd11223344"
        data_upper = "9F2608AABBCCDD11223344"
        result_lower = parse_emv_data(data_lower)
        result_upper = parse_emv_data(data_upper)
        assert result_lower == result_upper

    def test_parse_truncated_value(self):
        """Test handling truncated value gracefully."""
        # Length says 8 bytes but only 4 provided
        data = "9F2608AABBCCDD"
        result = parse_emv_data(data)
        assert "9F26" in result
        # Should take what's available
        assert result["9F26"] == "AABBCCDD"

    def test_parse_common_tags(self):
        """Test parsing common EMV tags found in Field 55."""
        data = (
            "9F2608AABBCCDD11223344"  # Application Cryptogram
            "9F2701809F100706010A03A4B800"  # CID + Issuer App Data
            "9F3704123456789F36020001"  # Unpredictable Number + ATC
            "950500000000009A03251215"  # TVR + Transaction Date
            "9C01005F2A020840"  # Transaction Type + Currency
            "82021980"  # AIP
            "9F1A020840"  # Terminal Country Code
        )
        result = parse_emv_data(data)

        assert result.get("9F26") == "AABBCCDD11223344"
        assert result.get("9F27") == "80"
        assert result.get("9F10") == "06010A03A4B800"
        assert result.get("9F37") == "12345678"
        assert result.get("9F36") == "0001"
        assert result.get("95") == "0000000000"
        assert result.get("9A") == "251215"
        assert result.get("9C") == "00"
        assert result.get("5F2A") == "0840"
        assert result.get("82") == "1980"
        assert result.get("9F1A") == "0840"


class TestBuildEmvData:
    """Tests for build_emv_data function."""

    def test_build_single_tag(self):
        """Test building single EMV tag."""
        tags = {"9F26": "AABBCCDD11223344"}
        result = build_emv_data(tags)
        assert result == "9F2608AABBCCDD11223344"

    def test_build_multiple_tags(self):
        """Test building multiple EMV tags."""
        tags = {"9F26": "AABBCCDD11223344", "9F27": "80"}
        result = build_emv_data(tags)
        # Should contain both tags
        assert "9F2608AABBCCDD11223344" in result
        assert "9F270180" in result

    def test_build_short_length(self):
        """Test building with short length encoding (< 128 bytes)."""
        tags = {"9A": "251215"}  # 3 bytes
        result = build_emv_data(tags)
        assert result == "9A03251215"

    def test_build_medium_length(self):
        """Test building with medium length encoding (128-255 bytes)."""
        value = "AA" * 130  # 130 bytes
        tags = {"9F10": value}
        result = build_emv_data(tags)
        assert result == f"9F1081{130:02X}{value}"

    def test_build_long_length(self):
        """Test building with long length encoding (> 255 bytes)."""
        value = "BB" * 300  # 300 bytes
        tags = {"9F10": value}
        result = build_emv_data(tags)
        assert result == f"9F1082{300:04X}{value}"

    def test_build_empty(self):
        """Test building with empty tags."""
        tags = {}
        result = build_emv_data(tags)
        assert result == ""

    def test_build_normalizes_case(self):
        """Test that build normalizes to uppercase."""
        tags = {"9f26": "aabbccdd11223344"}
        result = build_emv_data(tags)
        assert result == "9F2608AABBCCDD11223344"

    def test_roundtrip(self):
        """Test that build and parse are inverse operations."""
        original_tags = {
            "9F26": "AABBCCDD11223344",
            "9F27": "80",
            "9F10": "06010A03A4B800",
            "95": "0000000000",
        }
        built = build_emv_data(original_tags)
        parsed = parse_emv_data(built)
        assert parsed == original_tags


class TestGetTagName:
    """Tests for get_tag_name function."""

    def test_known_tags(self):
        """Test getting names for known tags."""
        assert get_tag_name("9F26") == "Application Cryptogram"
        assert get_tag_name("9F27") == "Cryptogram Information Data"
        assert get_tag_name("95") == "Terminal Verification Results (TVR)"
        assert get_tag_name("9A") == "Transaction Date"

    def test_unknown_tag(self):
        """Test getting name for unknown tag."""
        assert get_tag_name("FFFF") == "Unknown"
        assert get_tag_name("AA") == "Unknown"

    def test_case_insensitive(self):
        """Test that tag lookup is case insensitive."""
        assert get_tag_name("9f26") == get_tag_name("9F26")


class TestExplainTvr:
    """Tests for explain_tvr function."""

    def test_all_zeros(self):
        """Test TVR with no flags set."""
        issues = explain_tvr("0000000000")
        assert issues == []

    def test_offline_data_auth_not_performed(self):
        """Test TVR byte 1 bit 8."""
        issues = explain_tvr("8000000000")
        assert "Offline data authentication not performed" in issues

    def test_sda_failed(self):
        """Test TVR byte 1 bit 7."""
        issues = explain_tvr("4000000000")
        assert "SDA failed" in issues

    def test_expired_application(self):
        """Test TVR byte 2 bit 7."""
        issues = explain_tvr("0040000000")
        assert "Expired application" in issues

    def test_pin_try_limit_exceeded(self):
        """Test TVR byte 3 bit 6."""
        issues = explain_tvr("0000200000")
        assert "PIN Try Limit exceeded" in issues

    def test_exceeds_floor_limit(self):
        """Test TVR byte 4 bit 8."""
        issues = explain_tvr("0000008000")
        assert "Transaction exceeds floor limit" in issues

    def test_issuer_auth_failed(self):
        """Test TVR byte 5 bit 7."""
        issues = explain_tvr("0000000040")
        assert "Issuer authentication failed" in issues

    def test_multiple_flags(self):
        """Test TVR with multiple flags set."""
        # Byte 1: 0x80 (offline not performed) + 0x40 (SDA failed) = 0xC0
        issues = explain_tvr("C000000000")
        assert "Offline data authentication not performed" in issues
        assert "SDA failed" in issues

    def test_short_tvr_padded(self):
        """Test that short TVR is padded with zeros."""
        issues = explain_tvr("80")  # Only 1 byte
        assert "Offline data authentication not performed" in issues


class TestExplainCid:
    """Tests for explain_cid function."""

    def test_aac(self):
        """Test AAC cryptogram (bits 7-6 = 00)."""
        result = explain_cid("00")
        assert "AAC" in result
        assert "declined" in result.lower()

    def test_tc(self):
        """Test TC cryptogram (bits 7-6 = 01)."""
        result = explain_cid("40")
        assert "TC" in result
        assert "approved offline" in result.lower()

    def test_arqc(self):
        """Test ARQC cryptogram (bits 7-6 = 10)."""
        result = explain_cid("80")
        assert "ARQC" in result
        assert "online" in result.lower()

    def test_rfu(self):
        """Test RFU cryptogram (bits 7-6 = 11)."""
        result = explain_cid("C0")
        assert "RFU" in result

    def test_empty_cid(self):
        """Test empty CID defaults to AAC."""
        result = explain_cid("")
        assert "AAC" in result


class TestEmvTags:
    """Tests for EMV_TAGS constant."""

    def test_tags_dict_not_empty(self):
        """Test that EMV_TAGS dictionary is populated."""
        assert len(EMV_TAGS) > 50  # Should have many tags defined

    def test_common_tags_present(self):
        """Test that common tags are defined."""
        common_tags = ["9F26", "9F27", "9F10", "95", "9A", "9C", "82", "5F2A"]
        for tag in common_tags:
            assert tag in EMV_TAGS, f"Common tag {tag} should be in EMV_TAGS"

    def test_tags_have_descriptions(self):
        """Test that all tags have non-empty descriptions."""
        for tag, desc in EMV_TAGS.items():
            assert desc, f"Tag {tag} should have a description"
            assert len(desc) > 2, f"Tag {tag} description too short"
