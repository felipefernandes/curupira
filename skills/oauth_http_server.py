"""
Servidor HTTP temporário para capturar callback OAuth2
Usado durante autenticação com Google Calendar
"""
import asyncio
import logging
from aiohttp import web  # type: ignore
from typing import Optional
from urllib.parse import parse_qs, urlparse


class OAuthCallbackServer:
    """
    Servidor HTTP local para capturar authorization code do OAuth2.

    Lifecycle:
    1. Inicia em http://127.0.0.1:8080
    2. Aguarda callback do Google
    3. Extrai 'code' da query string
    4. Fecha automaticamente
    """

    def __init__(self, port: int = 8080, timeout: int = 300):
        """
        Args:
            port: Porta do servidor (default: 8080)
            timeout: Timeout em segundos (default: 5 min)
        """
        self.port = port
        self.timeout = timeout
        self.logger = logging.getLogger("OAuthCallbackServer")
        self.auth_code: Optional[str] = None
        self.state: Optional[str] = None
        self.error: Optional[str] = None
        self._server_task: Optional[asyncio.Task] = None
        self._code_received = asyncio.Event()

    async def _handle_callback(self, request: web.Request) -> web.Response:
        """Handle OAuth2 callback request."""
        try:
            # Extrai parâmetros da query string
            self.auth_code = request.query.get('code')
            self.state = request.query.get('state')
            self.error = request.query.get('error')

            # Sinaliza que código foi recebido
            self._code_received.set()

            if self.error:
                error_desc = request.query.get('error_description', 'Erro desconhecido')
                self.logger.error(f"OAuth error: {self.error} - {error_desc}")
                return web.Response(
                    text=f"❌ Erro na autenticação: {error_desc}\n\nVocê pode fechar esta janela.",
                    content_type="text/html; charset=utf-8"
                )

            if not self.auth_code:
                self.logger.warning("Callback recebido sem código de autorização")
                return web.Response(
                    text="❌ Nenhum código de autorização recebido.\n\nVocê pode fechar esta janela.",
                    content_type="text/html; charset=utf-8"
                )

            self.logger.info(f"Authorization code recebido (tamanho: {len(self.auth_code)})")

            return web.Response(
                text=(
                    "✅ Autenticação concluída com sucesso!\n\n"
                    "Você pode fechar esta janela e voltar para o Telegram."
                ),
                content_type="text/html; charset=utf-8"
            )

        except Exception as e:
            self.logger.error(f"Erro no callback handler: {e}")
            return web.Response(
                text=f"❌ Erro ao processar callback: {e}\n\nVocê pode fechar esta janela.",
                content_type="text/html; charset=utf-8"
            )

    async def start(self) -> str:
        """
        Inicia o servidor e retorna a URL de callback.

        Returns:
            URL do callback (ex: "http://127.0.0.1:8080/callback")
        """
        app = web.Application()
        app.router.add_get('/callback', self._handle_callback)

        runner = web.AppRunner(app)
        await runner.setup()

        site = web.TCPSite(runner, '127.0.0.1', self.port)
        await site.start()

        callback_url = f"http://127.0.0.1:{self.port}/callback"
        self.logger.info(f"OAuth callback server iniciado em {callback_url}")

        # Armazena runner para cleanup posterior
        self._runner = runner

        return callback_url

    async def wait_for_code(self) -> Optional[str]:
        """
        Aguarda código de autorização ser recebido.

        Returns:
            Authorization code ou None se timeout/erro
        """
        try:
            await asyncio.wait_for(
                self._code_received.wait(),
                timeout=self.timeout
            )
            return self.auth_code
        except asyncio.TimeoutError:
            self.logger.warning(f"Timeout após {self.timeout}s aguardando código")
            return None

    async def stop(self):
        """Para o servidor."""
        if hasattr(self, '_runner'):
            await self._runner.cleanup()
            self.logger.info("OAuth callback server encerrado")


def extract_code_from_url(url: str) -> Optional[str]:
    """
    Extrai código de autorização de uma URL de callback.

    Útil para fallback manual quando servidor não está acessível.

    Args:
        url: URL completa (ex: "http://127.0.0.1:8080/callback?code=ABC&state=XYZ")

    Returns:
        Authorization code ou None

    Example:
        >>> url = "http://127.0.0.1:8080/callback?code=4/0AY0e-g6..."
        >>> extract_code_from_url(url)
        "4/0AY0e-g6..."
    """
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        code = params.get('code', [None])[0]
        return code
    except Exception:
        return None
