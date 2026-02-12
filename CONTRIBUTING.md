# Contribuindo para o CurupiraBOT

## 🧜‍♀️ Code Review com Iara

O CurupiraBOT utiliza uma agente de IA chamada **Iara** para realizar revisões automáticas de código. Para garantir a qualidade e segurança do projeto, **toda alteração de código deve passar por ela**.

> ℹ️ **Nota**: A Iara agora possui seu próprio repositório com instruções detalhadas de instalação e uso local: [https://github.com/felipefernandes/iara](https://github.com/felipefernandes/iara).

### Fluxo Obrigatório

1.  **Nunca commite diretamente na `main`**.
2.  Crie uma branch para sua feature ou correção:
    ```bash
    git checkout -b feature/minha-feature
    ```
3.  Faça seus commits e envie para o repositório remoto:
    ```bash
    git push origin feature/minha-feature
    ```
4.  **Abra um Pull Request (PR)** contra a branch `main`.
5.  Aguarde o comentário da Iara no PR.
    - Ela analisará segurança, performance, bugs e boas práticas.
    - Se ela solicitar mudanças, faça os ajustes na mesma branch e dê push novamente.
6.  O merge só deve ser feito após a aprovação da Iara (e de revisores humanos, se houver).

---

## Padrões de Projeto

- **Commits:** Use [Conventional Commits](https://www.conventionalcommits.org/) (ex: `feat:`, `fix:`, `docs:`).
- **Código:** Siga a PEP 8 para Python.
- **Testes:** Adicione testes unitários/integração para novas funcionalidades em `tests/`.

## 🏗️ Estrutura & Padrões (OpenSpec)

Este projeto utiliza uma metodologia leve de especificações chamada **OpenSpec** para manter o código organizado.

1.  **Mudanças Grandes?**
    *   Evite mudar código diretamente.
    *   Crie uma proposta em `openspec/changes/nova-feature/`.
    *   Consulte `openspec/project.md` e `openspec/AGENTS.md` para entender a arquitetura.

## 🗺️ Roadmap

Confira o arquivo [ROADMAP.md](ROADMAP.md) para ver as próximas fases planejadas.
