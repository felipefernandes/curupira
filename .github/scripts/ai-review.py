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

# Configuração da API OpenRouter
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

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


def get_free_models() -> list:
    """Consulta a API do OpenRouter para encontrar modelos gratuitos disponíveis."""
    try:
        req = urllib.request.Request(OPENROUTER_MODELS_URL)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            
        free_models = []
        for model in data.get("data", []):
            pricing = model.get("pricing", {})
            # Verifica se o preço é zero (string ou number)
            p_prompt = str(pricing.get("prompt", "1"))
            p_completion = str(pricing.get("completion", "1"))
            
            if p_prompt == "0" and p_completion == "0":
                # Prioriza modelos 'google' e 'meta' que costumam ser melhores p/ código
                if "gemini" in model["id"] or "llama" in model["id"]:
                    free_models.insert(0, model["id"])
                else:
                    free_models.append(model["id"])
                    
        return free_models
    except Exception as e:
        print(f"⚠️ Erro ao listar modelos: {e}", file=sys.stderr)
        # Fallback para IDs que 'deveriam' existir se a listagem falhar
        return [
            "google/gemini-2.0-flash-exp:free",
            "meta-llama/llama-3-8b-instruct:free"
        ]


def review_code_with_model(diff: str, api_key: str, model: str) -> str:
    """Tenta revisar com um modelo específico."""
    max_chars = 15000
    if len(diff) > max_chars:
        diff = diff[:max_chars] + "\n\n[... diff truncado por limite de tamanho ...]"
    
    # Payload simplificado para máxima compatibilidade
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Revise o seguinte diff de código:\n\n```diff\n{diff}\n```"}
        ],
        "temperature": 0.3, # Baixa temperatura é seguro
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
                 # Se a API retornar 200 OK mas com JSON de erro
                 raise Exception(f"API Error: {result['error']}")
            
            # Tratamento robusto de resposta (alguns modelos retornam estruturas levemente diferentes)
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            else:
                return "⚠️ Modelo retornou resposta vazia."

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise Exception(f"HTTP Error {e.code}: {error_body}")


def review_code(diff: str, api_key: str) -> str:
    """It era sobre modelos gratuitos até conseguir sucesso."""
    if not diff.strip():
        return "✅ Nenhuma alteração de código para revisar."
    
    # Busca dinâmica
    print("🔄 Buscando modelos gratuitos disponíveis...", file=sys.stderr)
    models = get_free_models()
    
    if not models:
        return "❌ Nenhum modelo gratuito encontrado na API do OpenRouter no momento."
        
    print(f"✅ Modelos encontrados: {len(models)} ({', '.join(models[:3])}...)", file=sys.stderr)
    
    errors = []
    
    # Tenta os top 5 encontrados
    for model in models[:5]:
        try:
            print(f"🔄 Tentando modelo: {model}...", file=sys.stderr)
            return review_code_with_model(diff, api_key, model)
        except Exception as e:
            error_msg = str(e)
            print(f"⚠️ Falha no modelo {model}: {error_msg}", file=sys.stderr)
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
