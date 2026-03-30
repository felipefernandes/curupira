---
trigger: model_decision
description: Sempre que um arquivo `.py` for alterado de forma significativa ou um novo endpoint/função for criado.
---

# Rule: Documentation Maintenance

**Ações**:
1. Analise se a mudança afeta o `README.md` ou o `ROADMAP.md`.
2. Se houver novas variáveis de ambiente, verifique o `.env.example`.
3. Se houver novas configurações, verifique a necessidade de incluí-las no `default.config.toml`
4. Se o código for complexo, sugira a criação de um comentário de bloco (Docstring) no padrão Google/NumPy.
5. **Proatividade**: Não pergunte "devo atualizar?". Apenas prepare o rascunho da atualização no Artifact e diga: "Atualizei a documentação para refletir a nova lógica de X".