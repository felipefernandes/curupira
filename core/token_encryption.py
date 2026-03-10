"""
Token Encryption at Rest
========================
Criptografa tokens OAuth2 armazenados em disco usando Fernet (AES-128-CBC + HMAC-SHA256).

Segurança:
- Chave derivada de TELEGRAM_TOKEN via PBKDF2 (100k iterações)
- Proteção se data/ for exposto (backup em cloud, acesso físico)
- Backward compatible: se descriptografia falhar, re-autenticação necessária

⚠️ IMPORTANTE:
Se TELEGRAM_TOKEN mudar, tokens ficam inacessíveis (usuário precisa re-autenticar)
"""

import base64
import hashlib
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken

from core.config import TELEGRAM_TOKEN


class TokenCipher:
    """
    Criptografia de tokens usando chave derivada de TELEGRAM_TOKEN.

    Implementa Fernet (symmetric encryption):
    - AES-128-CBC para criptografia
    - HMAC-SHA256 para autenticação
    - Timestamp para verificação de idade do token
    """

    @staticmethod
    def _get_encryption_key() -> bytes:
        """
        Deriva chave de criptografia Fernet (32 bytes) de TELEGRAM_TOKEN.

        Uses PBKDF2 (Password-Based Key Derivation Function 2):
        - Algoritmo: HMAC-SHA256
        - Iterações: 100,000 (OWASP recomenda 100k+ para 2023)
        - Salt: Fixo e específico para esta aplicação

        Returns:
            Chave Fernet (32 bytes, base64-encoded)

        Raises:
            ValueError: Se TELEGRAM_TOKEN não estiver configurado
        """
        if not TELEGRAM_TOKEN:
            raise ValueError(
                "TELEGRAM_TOKEN não configurado - necessário para encryption. "
                "Configure TELEGRAM_TOKEN no .env antes de usar Google Calendar."
            )

        # Salt fixo (não precisa ser secreto, apenas consistente)
        # Específico para token encryption do Curupira
        salt = b"curupira_token_encryption_v1"

        # Derivar chave de 32 bytes usando PBKDF2-HMAC-SHA256
        key_material = hashlib.pbkdf2_hmac(
            'sha256',
            TELEGRAM_TOKEN.encode('utf-8'),
            salt,
            iterations=100000,  # 100k iterações (OWASP 2023)
            dklen=32  # 32 bytes para Fernet
        )

        # Fernet espera chave em base64
        return base64.urlsafe_b64encode(key_material)

    @staticmethod
    def encrypt_token(token_json: str) -> bytes:
        """
        Criptografa JSON do token.

        Args:
            token_json: Token em formato JSON string (de Credentials.to_json())

        Returns:
            Bytes criptografados (Fernet format)

        Raises:
            ValueError: Se TELEGRAM_TOKEN não estiver configurado
            Exception: Se criptografia falhar

        Example:
            >>> token_json = creds.to_json()
            >>> encrypted = TokenCipher.encrypt_token(token_json)
            >>> with open('data/google_token.json', 'wb') as f:
            ...     f.write(encrypted)
        """
        key = TokenCipher._get_encryption_key()
        cipher = Fernet(key)
        return cipher.encrypt(token_json.encode('utf-8'))

    @staticmethod
    def decrypt_token(encrypted_data: bytes) -> Optional[str]:
        """
        Descriptografa JSON do token.

        Args:
            encrypted_data: Bytes criptografados (Fernet format)

        Returns:
            Token JSON string ou None se falhar

        Failure Cases:
            - TELEGRAM_TOKEN mudou (chave diferente)
            - Dados corrompidos
            - Token expirado (se TTL foi configurado no Fernet)

        Example:
            >>> with open('data/google_token.json', 'rb') as f:
            ...     encrypted = f.read()
            >>> token_json = TokenCipher.decrypt_token(encrypted)
            >>> if token_json:
            ...     creds = Credentials.from_authorized_user_info(json.loads(token_json))
        """
        try:
            key = TokenCipher._get_encryption_key()
            cipher = Fernet(key)
            decrypted = cipher.decrypt(encrypted_data)
            return decrypted.decode('utf-8')

        except (InvalidToken, Exception):
            # Falha silenciosa: retorna None para forçar re-autenticação
            # Possíveis causas:
            # 1. TELEGRAM_TOKEN mudou
            # 2. Arquivo corrompido
            # 3. Formato inválido
            return None
