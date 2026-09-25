# Auditoria geral e informe fiscal

Data da revisão: 24 de setembro de 2026.

## Escopo analisado

Foram inspecionadas as camadas `views`, `controllers`, `services`, `models`,
`database`, `core` e `utilitarios`, além dos testes, temas, traduções e rotinas
de empacotamento. A arquitetura principal segue o fluxo View → Controller →
Service → Model. As telas ainda criam seus controladores, o que mantém algum
acoplamento com Qt, mas as regras financeiras críticas permanecem nos serviços
e modelos.

O levantamento estático encontrou muitos tratamentos genéricos de exceção,
principalmente na interface. Eles são adequados quando exibem uma mensagem e
registram o erro, mas 31 pontos da camada visual apenas ignoram falhas durante
fechamento de widgets. Esses pontos foram registrados como dívida técnica e não
foram alterados em massa, pois mudar destrutores e eventos de fechamento sem um
defeito reproduzível pode introduzir regressões.

## Falha fiscal encontrada

O antigo “Informe de Rendimentos” era um resumo financeiro: somava entradas e
saídas do extrato. Ele não possuía previdência oficial, previdência complementar,
pensão, IRRF, rendimentos isentos, tributação exclusiva ou RRA. Portanto, esses
valores não poderiam ser deduzidos de transações bancárias com segurança.

A Receita Federal determina que o comprovante seja fornecido pela fonte
pagadora e contenha os valores efetivamente pagos, as deduções efetivas e o
imposto retido. Informações inexatas podem gerar penalidade. Por isso, o Finance
Assist agora separa dois documentos:

- **Relatório financeiro auxiliar:** continua calculado pelas transações e deixa
  explícito que não classifica tributação ou dedutibilidade.
- **Modelo fiscal por fonte pagadora:** usa somente valores transcritos pelo
  usuário de um comprovante recebido. Nenhum campo fiscal é inferido do extrato.

## Implementação

- Nova tabela `informes_fiscais`, isolada por usuário, ano-calendário e documento
  da fonte. A criação é aditiva e não exclui nem regrava tabelas existentes.
- Cadastro pela tela de Relatórios, com validação algorítmica de CPF/CNPJ,
  obrigatoriedade da fonte e natureza, rejeição de valores negativos e campos
  dos quadros 1 a 7 do modelo da Receita.
- Seleção explícita entre relatório auxiliar e modelo fiscal; cada fonte gera
  seu próprio documento.
- PDF passou a quebrar linhas longas e restaurar a fonte ao iniciar nova página.
- Falhas nos observadores de idioma e tema agora são registradas, e a troca de
  idioma deixou de imprimir mensagens diretamente no terminal.

O texto fiscal inclui um aviso de conferência porque o Finance Assist não é a
fonte pagadora nem transmite eSocial/EFD-Reinf. O documento oficial recebido da
fonte continua sendo a referência para a declaração.

## Qualidade e riscos remanescentes

- Valores monetários ainda usam `REAL` em tabelas legadas. A migração global
  para centavos inteiros exige uma etapa própria com reconciliação dos saldos.
- A tradução manual cobre poucas chaves e usa Argos como complemento opcional.
  Sem o pacote do idioma, textos novos permanecem em português; não há perda de
  funcionalidade.
- Funções extensas no ciclo de fatura e no construtor de temas merecem divisão
  futura, mas estão cobertas pelos testes atuais e não foram reescritas sem uma
  necessidade funcional.

## Referências oficiais

- Instrução Normativa RFB nº 2.060/2021 — modelo do comprovante.
- Perguntas e Respostas DIRF 2025, seção 12 — obrigação, prazo e inexatidão.
- Perguntas e Respostas IRPF 2026 — orientação vigente para a declaração.
