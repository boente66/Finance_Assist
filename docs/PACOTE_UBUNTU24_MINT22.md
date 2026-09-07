# Variante Ubuntu 24.04 / Mint 22.x

Data: 7 de setembro de 2026. Versão da aplicação: 2.1.0-test.5.

## Solicitação e diagnóstico

Foi solicitada uma compilação separada para Ubuntu 24.04 após relato de falha
de instalação no Mint 22.2. O erro exato não foi fornecido. O Mint 22.x utiliza
a base Ubuntu 24.04 ([fonte oficial](https://www.linuxmint.com/rel_zara.php)).
A simulação `apt-get -s install` do DEB anterior no ambiente disponível, Mint
22.3, resolveu as dependências sem conflito. Isso não reproduz nem descarta
o problema específico do Mint 22.2; a causa original permanece não confirmada.

## Implementação

- Workflow dedicado `build-ubuntu24.yml`, com runner Ubuntu 24.04.
- Recompilação obrigatória por PyInstaller; não renomeia o binário Ubuntu 22.04.
- Arquivo separado `finance-assist_2.1.0-test.5_ubuntu24.04_amd64.deb`.
- Versão Debian `2.1.0~test5+ubuntu24.04.1`, mantendo `Package: finance-assist-test`.
- Dependências nativas Noble e bloqueio de libc anterior a 2.39.
- Mesmos caminhos da aplicação e dos dados; nenhuma alteração no schema,
  nas regras financeiras, controllers ou services.
- O build padrão anterior e os instaladores Windows não foram substituídos.

## Evidências

Commit de origem: `a3d629f7ab2378a78dc6d7426053ffa604c313ef`.
[Execução aprovada](https://github.com/boente66/Finance_Assist/actions/runs/34102270517).

| Verificação | Resultado |
|---|---|
| Suíte completa | APROVADO — 213 testes, 14 avisos de depreciação |
| Build nativo Ubuntu 24.04 e inventário das views | APROVADO |
| Instalação via apt do próprio artefato | APROVADO |
| Renderização XCB e OCR real | APROVADO |
| Banco novo sem usuários preexistentes | APROVADO |
| Preservação de banco sentinela e integrity_check | APROVADO |
| SHA256 do artefato baixado | APROVADO |
| Simulação apt da nova variante no Mint 22.3 | APROVADO — dependências resolvidas, nenhuma remoção |
| Executável extraído no Mint 22.3, Qt offscreen | APROVADO — 91 verificações, zero erros, saída 0 |
| Instalação real no Mint 22.2 | NÃO VERIFICADO |
| Causa do erro originalmente informado | NÃO CONFIRMADA — falta a mensagem |

O pacote é uma variante de teste adicionada à release existente. A tag original
da release não foi movida; o commit e a execução acima identificam a origem
específica desta compilação adicional. Instruções no README.

O teste Mint 22.3 não instalou o pacote nem abriu banco pessoal. Foram observados
avisos de IBus/inotify, telemetria ONNX e limitações do backend offscreen, sem
falha do processo; havia espaço em disco disponível. Isso não equivale a teste
de instalação nem homologação visual no Mint 22.2.
