"""Tests for PIN blocks and MACs.

Known-answer values were cross-checked against the independent psec library
(https://github.com/knovichikhin/psec) and the standard ISO 9564 format 0 example.
"""

import pytest

pytest.importorskip("cryptography")

from iso8583sim.core.builder import ISO8583Builder  # noqa: E402
from iso8583sim.core.types import ISO8583Message  # noqa: E402
from iso8583sim.core.validator import ISO8583Validator  # noqa: E402
from iso8583sim.security import (  # noqa: E402
    SecurityError,
    decode_pin_block,
    decrypt_pin_block,
    encode_pin_block,
    encrypt_pin_block,
    generate_mac,
    mac_field,
    sign_message,
    verify_mac,
    verify_message,
)

TDES_KEY = "0123456789ABCDEFFEDCBA9876543210"
AES_KEY = "00112233445566778899AABBCCDDEEFF"
PAN = "4111111111111111"
MAC_DATA = b"0200B220000000000000000000000000000012345678901234567890"


class TestPinBlockKnownAnswers:
    def test_format_0_clear(self):
        # subhadipmitra@: The textbook example: 041234FFFFFFFFFF XOR 0000111111111111.
        assert encode_pin_block("1234", PAN, 0).hex().upper() == "041225EEEEEEEEEE"

    def test_format_0_clear_long_pin(self):
        assert encode_pin_block("123456789012", "5555555555554444", 0).hex().upper() == "0C1261032DC546BB"

    def test_format_0_encrypted(self):
        assert encrypt_pin_block("1234", PAN, TDES_KEY, 0) == "2A3D408A1977DDE9"

    def test_format_4_decrypts_reference_block(self):
        # subhadipmitra@: Produced by psec. Format 4 has random fill, so the decrypt
        # direction is the stable known answer.
        assert decrypt_pin_block("B721A77A145836FEA3069AF20826FC13", PAN, AES_KEY, 4) == "1234"


class TestPinBlockRoundTrips:
    @pytest.mark.parametrize("fmt", [0, 1, 3])
    @pytest.mark.parametrize("pin", ["1234", "000000", "123456789012"])
    @pytest.mark.parametrize("key", [TDES_KEY, TDES_KEY + "0011223344556677"])
    def test_tdes_formats(self, fmt, pin, key):
        pan = None if fmt == 1 else PAN
        block = encrypt_pin_block(pin, pan, key, fmt)
        assert len(block) == 16
        assert decrypt_pin_block(block, pan, key, fmt) == pin

    @pytest.mark.parametrize("key", [AES_KEY, AES_KEY + "0011223344556677", AES_KEY * 2])
    @pytest.mark.parametrize("pan", [PAN, "4000123456789012345", "123456789012"])
    def test_format_4(self, key, pan):
        block = encrypt_pin_block("98765", pan, key, 4)
        assert len(block) == 32
        assert decrypt_pin_block(block, pan, key, 4) == "98765"

    def test_format_3_and_4_are_randomised(self):
        assert encode_pin_block("1234", PAN, 3) != encode_pin_block("1234", PAN, 3)
        assert encrypt_pin_block("1234", PAN, AES_KEY, 4) != encrypt_pin_block("1234", PAN, AES_KEY, 4)

    def test_clear_decode(self):
        assert decode_pin_block(bytes.fromhex("041225EEEEEEEEEE"), PAN, 0) == "1234"


class TestPinBlockErrors:
    @pytest.mark.parametrize("pin", ["123", "1234567890123", "12a4", ""])
    def test_invalid_pin(self, pin):
        with pytest.raises(SecurityError, match="PIN must be"):
            encode_pin_block(pin, PAN, 0)

    def test_format_0_needs_pan(self):
        with pytest.raises(SecurityError, match="needs the PAN"):
            encode_pin_block("1234", None, 0)

    def test_wrong_key_is_detected(self):
        block = encrypt_pin_block("1234", PAN, TDES_KEY, 0)
        # subhadipmitra@: A wrong key decrypts to random bytes, which fail one of the
        # structure checks (control nibble, length, digits or fill).
        with pytest.raises(SecurityError, match="Not a format|valid PIN|invalid fill"):
            decrypt_pin_block(block, PAN, "FEDCBA98765432100123456789ABCDEF", 0)

    def test_wrong_pan_is_detected(self):
        block = encrypt_pin_block("1234", PAN, AES_KEY, 4)
        with pytest.raises(SecurityError):
            decrypt_pin_block(block, "5555555555554444", AES_KEY, 4)

    @pytest.mark.parametrize("key", ["0011", "zz" * 16, TDES_KEY[:30]])
    def test_invalid_key(self, key):
        with pytest.raises(SecurityError, match="Key must be"):
            encrypt_pin_block("1234", PAN, key, 0)

    def test_format_4_has_no_clear_block(self):
        with pytest.raises(SecurityError, match="Format 4"):
            encode_pin_block("1234", PAN, 4)


class TestMacKnownAnswers:
    def test_retail_mac_padding_1(self):
        assert generate_mac(MAC_DATA, TDES_KEY, algorithm=3, padding=1) == "8C91711699F1CA5C"

    def test_retail_mac_padding_2(self):
        assert generate_mac(MAC_DATA, TDES_KEY, algorithm=3, padding=2) == "96B85620D0A83351"

    def test_cbc_mac_double_length(self):
        assert generate_mac(MAC_DATA, TDES_KEY, algorithm=1, padding=1) == "F268766218B202DD"

    def test_cbc_mac_single_des(self):
        assert generate_mac(MAC_DATA, TDES_KEY[:16], algorithm=1, padding=2) == "E8F511F047F4A51E"

    def test_str_is_ascii(self):
        assert generate_mac(MAC_DATA.decode(), TDES_KEY) == generate_mac(MAC_DATA, TDES_KEY)

    def test_truncated_mac(self):
        assert generate_mac(MAC_DATA, TDES_KEY, length=4) == "8C917116"


class TestMacVerification:
    def test_verify(self):
        assert verify_mac(MAC_DATA, "8C91711699F1CA5C", TDES_KEY)
        assert verify_mac(MAC_DATA, "8c917116", TDES_KEY)
        assert not verify_mac(MAC_DATA + b"0", "8C91711699F1CA5C", TDES_KEY)

    def test_invalid_options(self):
        with pytest.raises(SecurityError):
            generate_mac(MAC_DATA, TDES_KEY, algorithm=2)
        with pytest.raises(SecurityError):
            generate_mac(MAC_DATA, TDES_KEY, padding=3)
        with pytest.raises(SecurityError):
            generate_mac(MAC_DATA, TDES_KEY[:16], algorithm=3)


class TestMessageSigning:
    def message(self, extra=None):
        fields = {2: PAN, 3: "000000", 4: "000000001000", 11: "123456", **(extra or {})}
        return ISO8583Message(mti="0200", fields=fields)

    def test_primary_bitmap_uses_field_64(self):
        msg = self.message()
        raw = sign_message(msg, TDES_KEY)
        assert mac_field(msg.fields) == 64
        assert raw.endswith(msg.fields[64])
        assert verify_message(raw, TDES_KEY)

    def test_secondary_bitmap_uses_field_128(self):
        msg = self.message({70: "301"})
        raw = sign_message(msg, TDES_KEY)
        assert 128 in msg.fields and 64 not in msg.fields
        assert verify_message(raw, TDES_KEY)

    def test_tampering_is_detected(self):
        raw = sign_message(self.message(), TDES_KEY)
        tampered = raw.replace("000000001000", "000000009000")
        assert not verify_message(tampered, TDES_KEY)

    def test_wrong_key_fails(self):
        raw = sign_message(self.message(), TDES_KEY)
        assert not verify_message(raw, "FEDCBA98765432100123456789ABCDEF")

    def test_builder_and_validator_helpers(self):
        raw = ISO8583Builder().build_with_mac(self.message(), TDES_KEY, algorithm=1)
        assert ISO8583Validator().verify_mac(raw, TDES_KEY, algorithm=1)

    def test_message_without_mac(self):
        raw = ISO8583Builder().build(self.message())
        with pytest.raises(SecurityError, match="no MAC field"):
            verify_message(raw, TDES_KEY)
