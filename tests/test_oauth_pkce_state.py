"""
Tests para PKCE State Management (skills/oauth_pkce_state.py)
"""
import json
import pytest
from datetime import datetime, timedelta

from skills.oauth_pkce_state import PKCEState, PKCE_STATE_FILE


@pytest.fixture
def cleanup_pkce_state():
    """Remove arquivo PKCE state antes e depois de cada teste."""
    if PKCE_STATE_FILE.exists():
        PKCE_STATE_FILE.unlink()
    yield
    if PKCE_STATE_FILE.exists():
        PKCE_STATE_FILE.unlink()


class TestPKCEPairGeneration:
    """Testa geração de PKCE pair (code_verifier, code_challenge, state)."""

    def test_generate_pkce_pair_structure(self):
        """Verifica que generate_pkce_pair retorna estrutura correta."""
        pkce_pair = PKCEState.generate_pkce_pair()

        assert "code_verifier" in pkce_pair
        assert "code_challenge" in pkce_pair
        assert "state" in pkce_pair

    def test_code_verifier_format(self):
        """Verifica que code_verifier tem formato RFC 7636 compliant."""
        pkce_pair = PKCEState.generate_pkce_pair()
        code_verifier = pkce_pair["code_verifier"]

        # RFC 7636 §4.1: 43-128 chars [A-Z, a-z, 0-9, -, ., _, ~]
        assert 43 <= len(code_verifier) <= 128
        assert code_verifier.replace("-", "").replace("_", "").isalnum()

    def test_code_challenge_is_sha256_hash(self):
        """Verifica que code_challenge é SHA-256 do code_verifier."""
        import hashlib
        import base64

        pkce_pair = PKCEState.generate_pkce_pair()
        code_verifier = pkce_pair["code_verifier"]
        code_challenge = pkce_pair["code_challenge"]

        # Recomputar challenge manualmente
        expected_challenge_bytes = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        expected_challenge = base64.urlsafe_b64encode(expected_challenge_bytes).decode('utf-8').rstrip('=')

        assert code_challenge == expected_challenge

    def test_state_is_random(self):
        """Verifica que state é aleatório (dois calls geram values diferentes)."""
        pkce_pair1 = PKCEState.generate_pkce_pair()
        pkce_pair2 = PKCEState.generate_pkce_pair()

        assert pkce_pair1["state"] != pkce_pair2["state"]
        assert pkce_pair1["code_verifier"] != pkce_pair2["code_verifier"]


class TestPKCEStatePersistence:
    """Testa save/load de PKCE state."""

    def test_save_pkce_state_creates_file(self, cleanup_pkce_state):
        """Verifica que save_pkce_state cria arquivo corretamente."""
        state = "test_state_123"
        code_verifier = "test_verifier_abc"

        PKCEState.save_pkce_state(state, code_verifier)

        assert PKCE_STATE_FILE.exists()

    def test_save_pkce_state_content(self, cleanup_pkce_state):
        """Verifica que conteúdo salvo é JSON válido com campos corretos."""
        state = "test_state_123"
        code_verifier = "test_verifier_abc"

        PKCEState.save_pkce_state(state, code_verifier)

        with open(PKCE_STATE_FILE, "r") as f:
            data = json.load(f)

        assert data["state"] == state
        assert data["code_verifier"] == code_verifier
        assert "expires_at" in data

    def test_save_pkce_state_ttl(self, cleanup_pkce_state):
        """Verifica que TTL é ~10 minutos."""
        state = "test_state"
        code_verifier = "test_verifier"

        now = datetime.now()
        PKCEState.save_pkce_state(state, code_verifier)

        with open(PKCE_STATE_FILE, "r") as f:
            data = json.load(f)

        expires_at = datetime.fromisoformat(data["expires_at"])
        delta = expires_at - now

        # TTL deve ser ~10 min (com margem de 1 segundo para execução)
        assert 9.98 <= delta.total_seconds() / 60 <= 10.02

    def test_load_pkce_state_success(self, cleanup_pkce_state):
        """Verifica que load_pkce_state recupera code_verifier corretamente."""
        state = "test_state_456"
        code_verifier = "test_verifier_xyz"

        PKCEState.save_pkce_state(state, code_verifier)
        loaded_verifier = PKCEState.load_pkce_state(state)

        assert loaded_verifier == code_verifier

    def test_load_pkce_state_deletes_file(self, cleanup_pkce_state):
        """Verifica que load_pkce_state deleta arquivo (single-use)."""
        state = "test_state"
        code_verifier = "test_verifier"

        PKCEState.save_pkce_state(state, code_verifier)
        PKCEState.load_pkce_state(state)

        assert not PKCE_STATE_FILE.exists()

    def test_load_pkce_state_wrong_state(self, cleanup_pkce_state):
        """Verifica que load_pkce_state retorna None se state não corresponder."""
        PKCEState.save_pkce_state("correct_state", "verifier")
        result = PKCEState.load_pkce_state("wrong_state")

        assert result is None
        # Arquivo NÃO deve ser deletado se state não corresponder
        assert PKCE_STATE_FILE.exists()

    def test_load_pkce_state_no_file(self, cleanup_pkce_state):
        """Verifica que load_pkce_state retorna None se arquivo não existir."""
        result = PKCEState.load_pkce_state("any_state")
        assert result is None

    def test_load_pkce_state_expired(self, cleanup_pkce_state):
        """Verifica que load_pkce_state retorna None e deleta arquivo se expirado."""
        state = "expired_state"
        code_verifier = "expired_verifier"

        # Salvar com expiração no passado
        pkce_data = {
            "state": state,
            "code_verifier": code_verifier,
            "expires_at": (datetime.now() - timedelta(minutes=1)).isoformat()
        }

        with open(PKCE_STATE_FILE, "w") as f:
            json.dump(pkce_data, f)

        result = PKCEState.load_pkce_state(state)

        assert result is None
        assert not PKCE_STATE_FILE.exists()  # Arquivo deletado

    def test_load_pkce_state_corrupted_json(self, cleanup_pkce_state):
        """Verifica que load_pkce_state retorna None se JSON estiver corrompido."""
        with open(PKCE_STATE_FILE, "w") as f:
            f.write("invalid json {{{")

        result = PKCEState.load_pkce_state("any_state")
        assert result is None


class TestPKCEStateCleanup:
    """Testa cleanup de states expirados."""

    def test_cleanup_expired_removes_expired_file(self, cleanup_pkce_state):
        """Verifica que cleanup_expired remove arquivo expirado."""
        pkce_data = {
            "state": "expired",
            "code_verifier": "verifier",
            "expires_at": (datetime.now() - timedelta(minutes=1)).isoformat()
        }

        with open(PKCE_STATE_FILE, "w") as f:
            json.dump(pkce_data, f)

        PKCEState.cleanup_expired()

        assert not PKCE_STATE_FILE.exists()

    def test_cleanup_expired_keeps_valid_file(self, cleanup_pkce_state):
        """Verifica que cleanup_expired mantém arquivo válido."""
        pkce_data = {
            "state": "valid",
            "code_verifier": "verifier",
            "expires_at": (datetime.now() + timedelta(minutes=5)).isoformat()
        }

        with open(PKCE_STATE_FILE, "w") as f:
            json.dump(pkce_data, f)

        PKCEState.cleanup_expired()

        assert PKCE_STATE_FILE.exists()

    def test_cleanup_expired_no_file(self, cleanup_pkce_state):
        """Verifica que cleanup_expired não falha se arquivo não existir."""
        PKCEState.cleanup_expired()  # Não deve levantar exceção

    def test_cleanup_expired_corrupted_json(self, cleanup_pkce_state):
        """Verifica que cleanup_expired não falha com JSON corrompido."""
        with open(PKCE_STATE_FILE, "w") as f:
            f.write("corrupted")

        PKCEState.cleanup_expired()  # Não deve levantar exceção


class TestPKCEIntegration:
    """Testes de integração end-to-end."""

    def test_full_pkce_flow(self, cleanup_pkce_state):
        """Testa fluxo completo: gerar -> salvar -> carregar."""
        # Gerar PKCE pair
        pkce_pair = PKCEState.generate_pkce_pair()
        state = pkce_pair["state"]
        code_verifier = pkce_pair["code_verifier"]

        # Salvar
        PKCEState.save_pkce_state(state, code_verifier)

        # Carregar
        loaded_verifier = PKCEState.load_pkce_state(state)

        assert loaded_verifier == code_verifier
        assert not PKCE_STATE_FILE.exists()  # Arquivo deletado após uso
