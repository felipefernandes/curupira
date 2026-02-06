#!/usr/bin/env python3
"""
Iara - Revisora de Código do Projeto Curupira
Script para revisão automatizada de código usando IA (DeepSeek V3).
Parte do projeto Curupira - Inteligência Agêntica para Todos.
"""

import os
import sys
import json
import urllib.request
import urllib.error

# Configuração da API DeepSeek (compatível com OpenAI)
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"  # DeepSeek V3

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
- Seja construtivo e específico
- Aponte linha/função do problema
- Sugira correção quando possível
- Se não houver problemas: "✅ Código alinhado ao Manifesto Curupira"
"""


def review_code(diff: str, api_key: str) -> str:
    """
    Envia o diff para DeepSeek V3 e retorna a análise.
    
    Args:
        diff: O diff do código a ser revisado
        api_key: Chave da API DeepSeek
        
    Returns:
        String com a análise do código
    """
    if not diff.strip():
        return "✅ Nenhuma alteração de código para revisar."
    
    # Limitar tamanho do diff para evitar custos excessivos
    max_chars = 15000
    if len(diff) > max_chars:
        diff = diff[:max_chars] + "\n\n[... diff truncado por limite de tamanho ...]"
    
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Revise o seguinte diff de código:\n\n```diff\n{diff}\n```"}
        ],
        "temperature": 0.3,  # Mais determinístico para revisões consistentes
        "max_tokens": 2000
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(DEEPSEEK_API_URL, data=data, headers=headers)
        
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
            
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else "Sem detalhes"
        return f"❌ Erro na API DeepSeek ({e.code}): {error_body}"
    except urllib.error.URLError as e:
        return f"❌ Erro de conexão: {e.reason}"
    except Exception as e:
        return f"❌ Erro inesperado: {str(e)}"


def main():
    """Ponto de entrada principal."""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    
    if not api_key:
        print("❌ Erro: DEEPSEEK_API_KEY não configurada.", file=sys.stderr)
        sys.exit(1)
    
    # Lê o diff da variável de ambiente ou stdin
    diff = os.environ.get("PR_DIFF", "")
    if not diff:
        diff = sys.stdin.read()
    
    review = review_code(diff, api_key)
    print(review)


if __name__ == "__main__":
    main()
