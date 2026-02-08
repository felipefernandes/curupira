#!/usr/bin/env python3
"""
Iara - Revisora de Código do Projeto Curupira
Script para revisão automatizada de código usando IA via OpenRouter (Modelos Gratuitos).
Parte do projeto Curupira - Inteligência Agêntica para Todos.
"""

import os
import sys
import json
import urllib.request
import urllib.error
import time
import re

# Configuração da API OpenRouter
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Lista simplificada de modelos gratuitos e meta-modelos
FREE_MODELS = [
    "openrouter/free",              # Meta-modelo: O OpenRouter escolhe o melhor grátis disponível (ordem varia)
    "google/gemini-2.0-flash-lite-preview-02-05:free", # Muito rápido e estável
    "deepseek/deepseek-r1:free",    # DeepSeek R1 (pode estar congestionado)
    "meta-llama/llama-3-8b-instruct:free" # Leve e confiável
]

SYSTEM_PROMPT = """Você é um revisor de código especializado do **projeto Curupira** - um assistente de IA agêntica projetado para rodar em hardware limitado (Raspberry Pi 3, 1GB RAM).

## FILOSOFIA DO PROJETO (Manifesto Curupira):
- **Democratização**: Funciona em hardware modesto
- **Eficiência "Diet"**: Processamento inteligente, lógica leve
- **Acessibilidade**: Código como tutorial (didático)
- **Segurança**: Validação estrita de usuários, proteção de dados

## CHECKLIST DE REVISÃO:

### 🐛 BUGS POTENCIAIS
- Erros lógicos, condições de corrida
- Null/None sem tratamento
- Loops infinitos, recursão sem saída
- Async/await mal utilizados (deadlocks)

### 🔒 SEGURANÇA
- Secrets/tokens hardcoded
- SQL injection, command injection
- Validação de input de usuário
- Permissões excessivas (AUTHORIZED_USER_ID)

### ⚡ EFICIÊNCIA "DIET" (CRÍTICO)
- Importações pesadas: Pandas, Numpy, TensorFlow
- Carregamento de arquivos grandes na memória
- Loops bloqueantes (usar async quando possível)
- Context managers não usados (with open...)
- SQLite sem índices em queries frequentes

### 📚 QUALIDADE DE CÓDIGO
- Docstrings ausentes em funções públicas
- Variáveis com nomes obscuros
- Código duplicado (DRY)
- Try-except muito genéricos

## FORMATO DA RESPOSTA:
- **Papel**: Você é um CRÍTICO (Reviewer). Você NÃO é o autor do código. NÃO use frases como "Corrigi...", "Adicionei...". Use "Sugiro corrigir...", "O código deve...".
- **Objetivo**: Encontrar bugs, falhas de segurança e violações do Manifesto Curupira.
- **Saída**:
  - Liste os problemas encontrados de forma pontual.
  - Se sugerir código, use blocos pequenos de exemplo, NÃO gere diffs inteiros do arquivo.
  - ⛔ **PROIBIDO**: Gerar blocos de `diff` ou `patch`.
  - ⛔ **PROIBIDO**: Reescrever o arquivo todo.
  
- ✅ CASO DE SUCESSO (Sem bugs/problemas): Responda APENAS: "✅ **Aprovação Iara**: Código limpo, seguro e alinhado ao Manifesto. Pode fazer o merge! 🚀"
"""


def review_code_with_model(diff: str, api_key: str, model: str) -> str:
    """Tenta revisar com um modelo específico."""
    max_chars = 15000
    if len(diff) > max_chars:
        diff = diff[:max_chars] + "\n\n[... diff truncado por limite de tamanho ...]"
    
    # Payload simplificado
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Revise o seguinte diff de código:\n\n```diff\n{diff}\n```"}
        ],
        "temperature": 0.3, # Baixa temperatura é seguro
        "max_tokens": 6000, # Limite aumentado para evitar cortes (suporta DeepSeek R1 e Llama 3)
        # Headers HTTP Referer e X-Title são passados nos headers da request, não no payload json
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/felipefernandes/curupira",
        "X-Title": "Curupira Iara Reviewer"
    }
    
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(OPENROUTER_API_URL, data=data, headers=headers)
        
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
            if "error" in result:
                 raise Exception(f"API Error: {result['error']}")
            
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                
                # Strip <think> blocks (Common in DeepSeek R1)
                content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
                
                if not content:
                    raise ValueError("Modelo retornou conteúdo vazio (ou apenas tags <think>).")

                return content
            else:
                raise ValueError("API retornou sucesso mas sem 'choices'.")

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise Exception(f"HTTP Error {e.code}: {error_body}")


def review_code(diff: str, api_key: str) -> str:
    """
    Executa a revisão de código tentando múltiplos modelos gratuitos em sequência.
    Estratégia de Fallback:
    1. Tenta meta-modelo 'openrouter/free' (escolha automática)
    2. Tenta modelos específicos de alta qualidade (Gemini 2.0 Flash)
    3. Tenta modelos alternativos (DeepSeek R1, Llama 3)
     Se todos falharem, retorna mensagem de erro detalhada.
    """
    if not diff.strip():
        return "✅ Nenhuma alteração de código para revisar."
    
    errors = []
    
    print(f"🔄 Iniciando revisão com {len(FREE_MODELS)} modelos gratuitos...", file=sys.stderr)
    
    for model in FREE_MODELS:
        try:
            print(f"🔄 Tentando modelo: {model}...", file=sys.stderr)
            return review_code_with_model(diff, api_key, model)
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            error_msg = str(e)
            print(f"⚠️ Falha de conexão/HTTP no modelo {model}: {error_msg}", file=sys.stderr)
            errors.append(f"{model}: {error_msg}")
            time.sleep(1)
        except Exception as e:
            error_msg = str(e)
            print(f"⚠️ Erro inesperado no modelo {model}: {error_msg}", file=sys.stderr)
            errors.append(f"{model}: {error_msg}")
            time.sleep(1)
            
    return f"❌ Não foi possível revisar com nenhum modelo gratuito.\nErros:\n" + "\n".join(errors)


def main():
    """Ponto de entrada principal."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    
    if not api_key:
        print("❌ Erro: OPENROUTER_API_KEY não configurada.", file=sys.stderr)
        sys.exit(1)
    
    # Lê o diff da variável de ambiente ou stdin
    diff = os.environ.get("PR_DIFF", "")
    if not diff:
        diff = sys.stdin.read()
    
    review = review_code(diff, api_key)
    print(review)


if __name__ == "__main__":
    main()
