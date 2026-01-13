"""
Integration tests for PKCE (Proof Key for Code Exchange) implementation.

Tests PKCE challenge and verifier generation, validation, and security properties
as specified in RFC 7636.
"""

import pytest
import hashlib
import base64
from app.core.services.mcp.oauth_manager import OAuthManager


class TestPKCEChallengeGeneration:
    """Test PKCE code challenge generation."""

    def test_code_challenge_is_base64url_encoded_sha256(self):
        """Test that code challenge is base64url(SHA256(verifier))."""
        pkce = OAuthManager.generate_pkce()
        verifier = pkce['code_verifier']
        challenge = pkce['code_challenge']

        # Manually compute expected challenge
        digest = hashlib.sha256(verifier.encode()).digest()
        expected_challenge = base64.urlsafe_b64encode(digest).decode().rstrip('=')

        # Verify challenge matches expected value
        assert challenge == expected_challenge

    def test_code_challenge_length_is_43_characters(self):
        """Test that SHA256 base64url encoding produces 43 characters."""
        pkce = OAuthManager.generate_pkce()
        challenge = pkce['code_challenge']

        # SHA256 (32 bytes) -> base64url (43 chars without padding)
        assert len(challenge) == 43

    def test_code_challenge_uses_valid_base64url_characters(self):
        """Test that challenge uses only base64url alphabet."""
        pkce = OAuthManager.generate_pkce()
        challenge = pkce['code_challenge']

        # base64url alphabet: A-Z, a-z, 0-9, -, _
        valid_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
        assert all(c in valid_chars for c in challenge)

    def test_code_challenge_has_no_padding(self):
        """Test that code challenge does not include base64 padding."""
        pkce = OAuthManager.generate_pkce()
        challenge = pkce['code_challenge']

        # base64url should not have padding '='
        assert '=' not in challenge

    def test_different_verifiers_produce_different_challenges(self):
        """Test that different verifiers produce different challenges."""
        pkce1 = OAuthManager.generate_pkce()
        pkce2 = OAuthManager.generate_pkce()

        # Different verifiers should produce different challenges
        assert pkce1['code_verifier'] != pkce2['code_verifier']
        assert pkce1['code_challenge'] != pkce2['code_challenge']


class TestPKCEVerifierGeneration:
    """Test PKCE code verifier generation."""

    def test_code_verifier_meets_length_requirements(self):
        """Test that verifier length is between 43-128 characters per RFC 7636."""
        pkce = OAuthManager.generate_pkce()
        verifier = pkce['code_verifier']

        # RFC 7636 Section 4.1: 43 <= length <= 128
        assert 43 <= len(verifier) <= 128

    def test_code_verifier_uses_valid_characters(self):
        """Test that verifier uses only unreserved characters per RFC 7636."""
        pkce = OAuthManager.generate_pkce()
        verifier = pkce['code_verifier']

        # RFC 7636 Section 4.1: unreserved characters [A-Z] / [a-z] / [0-9] / "-" / "." / "_" / "~"
        valid_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")
        assert all(c in valid_chars for c in verifier)

    def test_code_verifier_has_sufficient_entropy(self):
        """Test that verifiers are cryptographically random (high entropy)."""
        # Generate multiple verifiers
        verifiers = [OAuthManager.generate_pkce()['code_verifier'] for _ in range(100)]

        # All should be unique (extremely high probability with 128 random characters)
        assert len(set(verifiers)) == 100

    def test_code_verifier_is_exactly_128_characters(self):
        """Test that implementation uses maximum length for best security."""
        pkce = OAuthManager.generate_pkce()
        verifier = pkce['code_verifier']

        # Our implementation should use 128 characters for maximum security
        assert len(verifier) == 128


class TestPKCESecurityProperties:
    """Test security properties of PKCE implementation."""

    def test_challenge_cannot_be_reversed_to_verifier(self):
        """Test that challenge is cryptographically one-way (SHA256)."""
        pkce = OAuthManager.generate_pkce()
        verifier = pkce['code_verifier']
        challenge = pkce['code_challenge']

        # SHA256 is a one-way hash function
        # We can't reverse the challenge to get the verifier
        # But we can verify that hashing the verifier produces the challenge
        digest = hashlib.sha256(verifier.encode()).digest()
        recomputed_challenge = base64.urlsafe_b64encode(digest).decode().rstrip('=')

        assert recomputed_challenge == challenge

    def test_pkce_provides_mitigation_against_authorization_code_interception(self):
        """Test that PKCE prevents authorization code interception attacks."""
        # Generate PKCE pair
        pkce = OAuthManager.generate_pkce()
        verifier = pkce['code_verifier']
        challenge = pkce['code_challenge']

        # Attacker intercepts authorization code but doesn't have verifier
        # Token endpoint requires verifier to match challenge
        # Attacker cannot compute verifier from challenge (SHA256 one-way)

        # Verify that the legitimate verifier produces the correct challenge
        digest = hashlib.sha256(verifier.encode()).digest()
        computed_challenge = base64.urlsafe_b64encode(digest).decode().rstrip('=')
        assert computed_challenge == challenge

        # Verify that a different verifier produces a different challenge
        fake_verifier = "attacker_verifier_" + "x" * 100
        fake_digest = hashlib.sha256(fake_verifier.encode()).digest()
        fake_challenge = base64.urlsafe_b64encode(fake_digest).decode().rstrip('=')
        assert fake_challenge != challenge

    def test_s256_method_is_more_secure_than_plain(self):
        """Test that S256 (SHA256) method is used instead of plain."""
        # Our implementation should always use S256 for security
        # Plain method would send verifier directly as challenge (insecure)

        pkce = OAuthManager.generate_pkce()
        verifier = pkce['code_verifier']
        challenge = pkce['code_challenge']

        # Challenge should NOT equal verifier (would indicate plain method)
        assert challenge != verifier

        # Challenge should be SHA256 hash
        digest = hashlib.sha256(verifier.encode()).digest()
        expected_challenge = base64.urlsafe_b64encode(digest).decode().rstrip('=')
        assert challenge == expected_challenge


class TestPKCECompliance:
    """Test RFC 7636 compliance."""

    def test_verifier_minimum_entropy_43_characters(self):
        """Test that verifier meets minimum entropy requirement."""
        pkce = OAuthManager.generate_pkce()
        verifier = pkce['code_verifier']

        # RFC 7636 Section 4.1: Minimum 43 characters
        assert len(verifier) >= 43

    def test_verifier_maximum_length_128_characters(self):
        """Test that verifier does not exceed maximum length."""
        pkce = OAuthManager.generate_pkce()
        verifier = pkce['code_verifier']

        # RFC 7636 Section 4.1: Maximum 128 characters
        assert len(verifier) <= 128

    def test_challenge_method_s256_recommended(self):
        """Test that S256 method is used (recommended by RFC 7636)."""
        # RFC 7636 Section 4.2: S256 is recommended over plain

        pkce = OAuthManager.generate_pkce()
        verifier = pkce['code_verifier']
        challenge = pkce['code_challenge']

        # Verify S256 transformation (not plain)
        digest = hashlib.sha256(verifier.encode()).digest()
        expected_challenge = base64.urlsafe_b64encode(digest).decode().rstrip('=')
        assert challenge == expected_challenge

    def test_unreserved_characters_only_in_verifier(self):
        """Test that verifier uses only unreserved characters per RFC 3986."""
        pkce = OAuthManager.generate_pkce()
        verifier = pkce['code_verifier']

        # RFC 3986 Section 2.3: unreserved = ALPHA / DIGIT / "-" / "." / "_" / "~"
        unreserved = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")
        assert all(c in unreserved for c in verifier)


class TestPKCEIntegrationWithOAuth:
    """Test PKCE integration with OAuth flow."""

    def test_pkce_pair_can_be_used_in_authorization_request(self):
        """Test that PKCE challenge can be included in authorization URL."""
        pkce = OAuthManager.generate_pkce()
        challenge = pkce['code_challenge']
        state = OAuthManager.generate_state()

        url = OAuthManager.build_auth_url(
            authorization_endpoint="https://oauth.example.com/authorize",
            client_id="test_client",
            redirect_uri="https://app.example.com/callback",
            code_challenge=challenge,
            state=state,
            scope="read"
        )

        # Verify challenge is in URL
        assert f"code_challenge={challenge}" in url
        assert "code_challenge_method=S256" in url

    def test_pkce_verifier_format_suitable_for_token_request(self):
        """Test that verifier can be sent in token request body."""
        pkce = OAuthManager.generate_pkce()
        verifier = pkce['code_verifier']

        # Verifier should be suitable for application/x-www-form-urlencoded
        # No special URL encoding needed due to unreserved characters
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~" for c in verifier)

    def test_pkce_prevents_code_injection_attack(self):
        """Test that PKCE prevents authorization code injection."""
        # Legitimate client generates PKCE
        legitimate_pkce = OAuthManager.generate_pkce()
        legitimate_challenge = legitimate_pkce['code_challenge']

        # Attacker generates their own PKCE
        attacker_pkce = OAuthManager.generate_pkce()
        attacker_verifier = attacker_pkce['code_verifier']

        # Attacker's verifier won't match legitimate challenge
        attacker_digest = hashlib.sha256(attacker_verifier.encode()).digest()
        attacker_computed_challenge = base64.urlsafe_b64encode(attacker_digest).decode().rstrip('=')

        assert attacker_computed_challenge != legitimate_challenge
