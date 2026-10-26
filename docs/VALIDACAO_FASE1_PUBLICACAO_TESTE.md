# Correções da Fase 1 — publicação para teste

As correções locais FA-001 a FA-005 foram enviadas ao GitHub por solicitação
do responsável pelo projeto. Esta publicação não homologa a Fase 1.

Permanecem pendentes os documentos legados inválidos em alguns fluxos de
edição, a completude e qualidade das traduções fixas e a validação manual
integral com fechamento e reabertura do aplicativo. A execução local
monolítica da suíte encerrou com falha nativa; seus resultados parciais
não representam aprovação da suíte completa.

## Bloqueio da recompilação em 26/10/2026

O [workflow Ubuntu/Mint](https://github.com/boente66/Finance_Assist/actions/runs/40418951087)
encerrou com 194 testes aprovados e uma falha no grupo A–M:
`test_revisao_exibe_status_resumo_e_selecao_segura`, em
`tests/integration/test_importacao_revisao_ui.py:56`.
A asserção recebeu `New` quando esperava `Novo`.

A causa já identificada na auditoria é o vazamento de estado dos testes
de catálogo offline: eles atribuem o idioma global, inclusive diretamente,
sem restaurá-lo ao terminar. Foi adicionada uma fixture local ao módulo
de testes que restaura o valor anterior com `monkeypatch`. As asserções
existentes e os requisitos de tradução permanecem os mesmos. Esta mudança
corrige o isolamento dos testes, não as pendências funcionais de idioma.

O ajuste preexistente no script de empacotamento Linux foi publicado em
commit separado das correções funcionais. Os pacotes continuam identificados
como versão de teste.
