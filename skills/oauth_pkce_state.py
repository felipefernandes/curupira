"""
PKCE State Management for OAuth2 Flow
======================================
Armazena code_verifier entre etapas do OAuth para evitar mismatch.

Este módulo implementa PKCE (Proof Key for Code Exchange) conforme RFC 7636
para proteção contra authorization code interception attacks.
"""

import json
import secrets
import hashlib
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict

DATA_DIR = Path(__file__).parent.parent / "data"
PKCE_STATE_FILE = DATA_DIR / "pkce_state.json"
PKCE_TTL_MINUTES = 10  # Google auth codes expiram em ~10 min


class PKCEState:
    """Gerencia state e code_verifier para PKCE flow."""

    @staticmethod
    def generate_pkce_pair() -> Dict[str, str]:
        """
        Gera code_verifier e code_challenge para PKCE.

        Returns:
            {"code_verifier": str, "code_challenge": str, "state": str}

        RFC 7636 Implementation:
        - code_verifier: 43-128 chars [A-Z, a-z, 0-9, -, ., _, ~]
        - code_challenge: BASE64URL(SHA256(code_verifier))
        - state: Random value para CSRF protection
        """
        # RFC 7636 §4.1: code_verifier = 43-128 chars
        code_verifier = base64.urlsafe_b64encode(
            secrets.token_bytes(32)
        ).decode('utf-8').rstrip('=')

        # RFC 7636 §4.2: code_challenge = BASE64URL(SHA256(code_verifier))
        challenge_bytes = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        code_challenge = base64.urlsafe_b64encode(
            challenge_bytes
        ).decode('utf-8').rstrip('=')

        # State para CSRF protection
        state = base64.urlsafe_b64encode(
            secrets.token_bytes(32)
        ).decode('utf-8').rstrip('=')

        return {
            "code_verifier": code_verifier,
            "code_challenge": code_challenge,
            "state": state
        }

    @staticmethod
    def save_pkce_state(state: str, code_verifier: str):
        """
        Salva code_verifier para uso posterior no token exchange.

        Args:
            state: State value (CSRF protection)
            code_verifier: Code verifier para PKCE

        Security:
            - TTL de 10 minutos (match com expiração de auth codes do Google)
            - Single-use: Deletado automaticamente após uso bem-sucedido
        """
        pkce_data = {
            "state": state,
            "code_verifier": code_verifier,
            "expires_at": (datetime.now() + timedelta(minutes=PKCE_TTL_MINUTES)).isoformat()
        }

        # Garantir que diretório existe
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        with open(PKCE_STATE_FILE, "w") as f:
            json.dump(pkce_data, f)

    @staticmethod
    def load_pkce_state(state: str) -> Optional[str]:
        """
        Carrega code_verifier se state corresponder e não estiver expirado.

        Args:
            state: State value recebido do OAuth flow

        Returns:
            code_verifier se válido, None caso contrário

        Side Effects:
            - Remove arquivo após uso bem-sucedido (single-use)
            - Remove arquivo se expirado
        """
        if not PKCE_STATE_FILE.exists():
            return None

        try:
            with open(PKCE_STATE_FILE, "r") as f:
                pkce_data = json.load(f)

            # Verificar state match (CSRF protection)
            if pkce_data.get("state") != state:
                return None

            # Verificar expiração
            expires_at = datetime.fromisoformat(pkce_data["expires_at"])
            if datetime.now() > expires_at:
                PKCE_STATE_FILE.unlink()  # Remover state expirado
                return None

            code_verifier = pkce_data["code_verifier"]

            # Single-use: remover após leitura bem-sucedida
            PKCE_STATE_FILE.unlink()

            return code_verifier

        except Exception:
            # Se houver qualquer erro de parsing, retornar None
            return None

    @staticmethod
    def cleanup_expired():
        """
        Remove states PKCE expirados.

        Chamado periodicamente para limpar states abandonados.
        """
        if not PKCE_STATE_FILE.exists():
            return

        try:
            with open(PKCE_STATE_FILE, "r") as f:
                pkce_data = json.load(f)

            expires_at = datetime.fromisoformat(pkce_data["expires_at"])
            if datetime.now() > expires_at:
                PKCE_STATE_FILE.unlink()
        except Exception:
            # Se houver erro ao ler, silenciosamente ignora
            pass
