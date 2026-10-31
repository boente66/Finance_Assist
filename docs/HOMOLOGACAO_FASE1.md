# Homologação final — Auditoria Fase 1

Em 31/10/2026, o responsável pelo projeto declarou o encerramento da Fase 1
da auditoria do Finance Assist por homologação humana.

## Escopo da autorização

- Fase 1: encerrada por declaração do responsável.
- Fase 2: aguardar autorização explícita de início.
- Divulgação de uma próxima versão: não autorizada até o fim da auditoria.
- Recompilação dos instaladores da versão de teste atual: autorizada.
- Atualização dos links diretos para acesso dos usuários finais: autorizada.

A recompilação usa as correções do commit
`54d973557c0d321d19200b187016e89cd0acd849`. Permanecem os identificadores
`2.1.0-test.17` e Debian `2.1.0~test17`; a publicação é uma recompilação da
versão de teste existente, sem lançamento de uma próxima versão.

## Evidências anteriores ao aceite

- Faturas: homologação manual informada pelo responsável.
- [Revisão de traduções e banco](REVISAO_TRADUCOES_E_BANCO_2026-10-31.md):
  372 testes aprovados, incluindo cobertura das 19 tabelas, persistência,
  rollback e chaves estrangeiras; textos fixos PT/EN/ES e persistência JSON.
- Os registros anteriores de pendência permanecem como histórico da auditoria.
  A declaração acima registra o aceite humano posterior.

## Ajuste necessário à recompilação macOS ARM

O executor `macos-14` foi cancelado pelo GitHub antes de executar o código,
durante a desativação programada da imagem. O [aviso do provedor](https://github.com/actions/runner-images/issues/13518)
orienta a migração para uma imagem suportada. O commit `80e3cc4` altera apenas
o executor ARM para `macos-15` e a asserção de metadados correspondente.
As fontes da aplicação e seus identificadores de versão permanecem iguais.
Este ajuste atende à recompilação autorizada e não inicia a Fase 2.
