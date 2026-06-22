"""
Tests para Token Encryption (core/token_encryption.py)
"""
import json
import pytest
from unittest.mock import patch

from core.token_encryption import TokenCipher


@pytest.fixture
def sample_token_json():
    """Token JSON de exemplo (simulando Credentials.to_json())."""
    return json.dumps({
        "token": "ya29.a0AfB_byC...",
        "refresh_token": "1//0g...",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "123456.apps.googleusercontent.com",
        "client_secret": "GOCSPX-abc123",
        "scopes": ["https://www.googleapis.com/auth/calendar.readonly"]
    })


class TestEncryptionKeyDerivation:
    """Testa derivação de chave de criptografia."""

    @patch('core.token_encryption.TELEGRAM_TOKEN', 'test_telegram_token_12345')
    def test_get_encryption_key_returns_valid_key(self):
        """Verifica que _get_encryption_key retorna chave Fernet válida."""
        key = TokenCipher._get_encryption_key()

        # Chave Fernet deve ser 44 bytes (32 bytes base64-encoded)
        assert len(key) == 44
        assert isinstance(key, bytes)

    @patch('core.token_encryption.TELEGRAM_TOKEN', None)
    def test_get_encryption_key_raises_if_no_telegram_token(self):
        """Verifica que _get_encryption_key levanta ValueError se TELEGRAM_TOKEN não configurado."""
        with pytest.raises(ValueError, match="TELEGRAM_TOKEN não configurado"):
            TokenCipher._get_encryption_key()

    @patch('core.token_encryption.TELEGRAM_TOKEN', 'test_token')
    def test_get_encryption_key_deterministic(self):
        """Verifica que mesma TELEGRAM_TOKEN sempre gera mesma chave."""
        key1 = TokenCipher._get_encryption_key()
        key2 = TokenCipher._get_encryption_key()

        assert key1 == key2

    @patch('core.token_encryption.TELEGRAM_TOKEN', 'test_token_1')
    def test_get_encryption_key_different_tokens_different_keys(self):
        """Verifica que TELEGRAM_TOKENs diferentes geram chaves diferentes."""
        key1 = TokenCipher._get_encryption_key()

        with patch('core.token_encryption.TELEGRAM_TOKEN', 'test_token_2'):
            key2 = TokenCipher._get_encryption_key()

        assert key1 != key2


class TestTokenEncryption:
    """Testa criptografia de tokens."""

    @patch('core.token_encryption.TELEGRAM_TOKEN', 'test_telegram_token_12345')
    def test_encrypt_token_returns_bytes(self, sample_token_json):
        """Verifica que encrypt_token retorna bytes."""
        encrypted = TokenCipher.encrypt_token(sample_token_json)

        assert isinstance(encrypted, bytes)
        assert len(encrypted) > 0

    @patch('core.token_encryption.TELEGRAM_TOKEN', 'test_telegram_token_12345')
    def test_encrypt_token_output_is_fernet_format(self, sample_token_json):
        """Verifica que output é formato Fernet válido (pode ser descriptografado)."""
        encrypted = TokenCipher.encrypt_token(sample_token_json)

        # Tentar descriptografar para verificar formato
        decrypted = TokenCipher.decrypt_token(encrypted)
        assert decrypted == sample_token_json

    @patch('core.token_encryption.TELEGRAM_TOKEN', 'test_telegram_token_12345')
    def test_encrypt_token_different_outputs_same_input(self, sample_token_json):
        """Verifica que Fernet gera outputs diferentes para mesmo input (nonce aleatório)."""
        encrypted1 = TokenCipher.encrypt_token(sample_token_json)
        encrypted2 = TokenCipher.encrypt_token(sample_token_json)

        # Outputs devem ser diferentes devido ao IV/nonce aleatório
        assert encrypted1 != encrypted2

    @patch('core.token_encryption.TELEGRAM_TOKEN', None)
    def test_encrypt_token_raises_if_no_telegram_token(self, sample_token_json):
        """Verifica que encrypt_token levanta ValueError se TELEGRAM_TOKEN não configurado."""
        with pytest.raises(ValueError, match="TELEGRAM_TOKEN não configurado"):
            TokenCipher.encrypt_token(sample_token_json)


class TestTokenDecryption:
    """Testa descriptografia de tokens."""

    @patch('core.token_encryption.TELEGRAM_TOKEN', 'test_telegram_token_12345')
    def test_decrypt_token_success(self, sample_token_json):
        """Verifica que decrypt_token recupera texto original."""
        encrypted = TokenCipher.encrypt_token(sample_token_json)
        decrypted = TokenCipher.decrypt_token(encrypted)

        assert decrypted == sample_token_json

    @patch('core.token_encryption.TELEGRAM_TOKEN', 'test_telegram_token_12345')
    def test_decrypt_token_wrong_key_returns_none(self, sample_token_json):
        """Verifica que decrypt_token retorna None se TELEGRAM_TOKEN mudou."""
        encrypted = TokenCipher.encrypt_token(sample_token_json)

        # Mudar TELEGRAM_TOKEN
        with patch('core.token_encryption.TELEGRAM_TOKEN', 'different_token'):
            decrypted = TokenCipher.decrypt_token(encrypted)

        assert decrypted is None

    @patch('core.token_encryption.TELEGRAM_TOKEN', 'test_telegram_token_12345')
    def test_decrypt_token_corrupted_data_returns_none(self):
        """Verifica que decrypt_token retorna None se dados estiverem corrompidos."""
        corrupted_data = b"this is not fernet encrypted data"
        decrypted = TokenCipher.decrypt_token(corrupted_data)

        assert decrypted is None

    @patch('core.token_encryption.TELEGRAM_TOKEN', 'test_telegram_token_12345')
    def test_decrypt_token_empty_data_returns_none(self):
        """Verifica que decrypt_token retorna None para dados vazios."""
        decrypted = TokenCipher.decrypt_token(b"")

        assert decrypted is None

    @patch('core.token_encryption.TELEGRAM_TOKEN', None)
    def test_decrypt_token_no_telegram_token_returns_none(self, sample_token_json):
        """Verifica que decrypt_token retorna None (não levanta exceção) se TELEGRAM_TOKEN não configurado."""
        # Primeiro criptografar com token válido
        with patch('core.token_encryption.TELEGRAM_TOKEN', 'test_token'):
            encrypted = TokenCipher.encrypt_token(sample_token_json)

        # Tentar descriptografar sem TELEGRAM_TOKEN
        decrypted = TokenCipher.decrypt_token(encrypted)

        assert decrypted is None


class TestEncryptionRoundTrip:
    """Testa fluxo completo encrypt -> decrypt."""

    @patch('core.token_encryption.TELEGRAM_TOKEN', 'test_telegram_token_12345')
    def test_round_trip_preserves_content(self, sample_token_json):
        """Verifica que encrypt -> decrypt preserva conteúdo original."""
        encrypted = TokenCipher.encrypt_token(sample_token_json)
        decrypted = TokenCipher.decrypt_token(encrypted)

        assert decrypted == sample_token_json

        # Verificar que JSON é válido
        assert decrypted is not None
        token_data = json.loads(decrypted)
        assert token_data["token"] == "ya29.a0AfB_byC..."

    @patch('core.token_encryption.TELEGRAM_TOKEN', 'test_telegram_token_12345')
    def test_round_trip_multiple_times(self, sample_token_json):
        """Verifica que múltiplos round trips preservam conteúdo."""
        for _ in range(5):
            encrypted = TokenCipher.encrypt_token(sample_token_json)
            decrypted = TokenCipher.decrypt_token(encrypted)
            assert decrypted == sample_token_json


class TestEdgeCases:
    """Testa casos extremos."""

    @patch('core.token_encryption.TELEGRAM_TOKEN', 'test_telegram_token_12345')
    def test_encrypt_empty_string(self):
        """Verifica que encrypt_token funciona com string vazia."""
        encrypted = TokenCipher.encrypt_token("")
        decrypted = TokenCipher.decrypt_token(encrypted)

        assert decrypted == ""

    @patch('core.token_encryption.TELEGRAM_TOKEN', 'test_telegram_token_12345')
    def test_encrypt_unicode_characters(self):
        """Verifica que encrypt_token funciona com caracteres Unicode."""
        unicode_json = json.dumps({"message": "Olá! 你好 مرحبا"})

        encrypted = TokenCipher.encrypt_token(unicode_json)
        decrypted = TokenCipher.decrypt_token(encrypted)

        assert decrypted == unicode_json

    @patch('core.token_encryption.TELEGRAM_TOKEN', 'test_telegram_token_12345')
    def test_encrypt_large_json(self):
        """Verifica que encrypt_token funciona com JSON grande."""
        large_json = json.dumps({
            "token": "a" * 10000,
            "data": ["item"] * 1000
        })

        encrypted = TokenCipher.encrypt_token(large_json)
        decrypted = TokenCipher.decrypt_token(encrypted)

        assert decrypted == large_json


class TestSecurityProperties:
    """Testa propriedades de segurança."""

    @patch('core.token_encryption.TELEGRAM_TOKEN', 'test_telegram_token_12345')
    def test_encrypted_data_not_readable(self, sample_token_json):
        """Verifica que dados criptografados não contêm texto original."""
        encrypted = TokenCipher.encrypt_token(sample_token_json)

        # Dados criptografados não devem conter partes visíveis do original
        assert b"ya29.a0AfB_byC" not in encrypted
        assert b"refresh_token" not in encrypted
        assert b"client_secret" not in encrypted

    @patch('core.token_encryption.TELEGRAM_TOKEN', 'test_telegram_token_12345')
    def test_pbkdf2_iterations_count(self):
        """Verifica que PBKDF2 usa 100k iterações (OWASP recommendation)."""
        # Este teste é mais conceitual - verifica indiretamente via tempo de execução
        # PBKDF2 com 100k iterações deve levar tempo mensurável (>0.01s)
        import time

        start = time.time()
        TokenCipher._get_encryption_key()
        elapsed = time.time() - start

        # Com 100k iterações, deve levar pelo menos 10ms
        assert elapsed > 0.01, "PBKDF2 parece estar usando poucas iterações"

    @patch('core.token_encryption.TELEGRAM_TOKEN', 'test_telegram_token_12345')
    def test_different_inputs_different_outputs(self):
        """Verifica que inputs diferentes geram outputs diferentes."""
        token1 = json.dumps({"token": "token1"})
        token2 = json.dumps({"token": "token2"})

        encrypted1 = TokenCipher.encrypt_token(token1)
        encrypted2 = TokenCipher.encrypt_token(token2)

        assert encrypted1 != encrypted2
