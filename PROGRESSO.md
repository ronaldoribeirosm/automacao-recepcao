# PROGRESSO.md

## Sessão 2026-07-22 (parte 2) — verificação end-to-end depois de liberar disco

Espaço em C: foi liberado (de ~67MB pra ~9,5GB livres), o que resolveu o `MemoryError`
intermitente e permitiu instalar o Playwright. Isso possibilitou uma validação bem
mais forte do que a da parte 1:

### O que foi validado de verdade agora

- **6 testes de integração novos** (`tests/test_pages_integration.py`) usando
  `streamlit.testing.v1.AppTest` — rodam o código real das 3 páginas (não só as
  funções puras), simulando clique de botão, preenchimento de campo, escolha de
  candidato ambíguo no rádio, e conferindo o `log.txt` gravado. Cloudbeds/Sheets
  são substituídos por dados fake nesse nível (não há API key real), mas todo o
  resto — sessão, diff, confirmação, gravação em dry-run — é código de produção
  rodando de verdade.
- Isso **encontrou e corrigiu 2 bugs reais** antes de irem pra produção:
  1. O campo "segundo dado" do Autopreenchimento sempre pré-preenchia com
     e-mail/telefone, mesmo quando a coluna configurada como segunda checagem
     era outra (ex.: CPF) — o match nunca fechava sozinho nesse caso. Corrigido
     em `pages/2_Autopreenchimento.py` pra usar o valor já existente no campo
     do Cloudbeds mapeado pra aquela coluna, com e-mail/telefone só como
     fallback.
  2. Quando dois candidatos ambíguos tinham nome, similaridade e status do
     segundo dado idênticos (o caso clássico de homônimos — exatamente o
     cenário que essa checagem existe pra cobrir), os rótulos do rádio de
     escolha colidiam e o usuário não conseguia escolher entre eles de verdade.
     Corrigido usando índice da lista como valor da opção em vez do texto
     formatado.
- **Navegador real** (Playwright + Chromium, headless): as 4 páginas (home +
  3 funções) foram abertas de verdade, screenshot tirado de cada uma — sem
  traceback visível, mensagens de "não configurado" aparecendo corretamente
  onde esperado. Navegação real pela sidebar testada (clique em
  "Autopreenchimento"). O toggle de dry-run foi clicado de verdade no DOM e
  confirmado que a faixa muda de "MODO TESTE" (âmbar) pra "MODO PRODUÇÃO"
  (vermelho) e volta.
- `pytest` roda limpo e reproduzível agora (22 testes, antes tinha `MemoryError`
  intermitente por falta de espaço em disco).

### O que ainda NÃO foi validado (só isso depende de credencial real)

- Nenhuma chamada real à API do Cloudbeds nem ao Google Sheets — segue
  pendente por não haver API key/credencial disponível. Os testes de
  integração cobrem toda a lógica em volta dessas chamadas (parsing,
  matching, diff, log), mas não os nomes exatos de campo/endpoint contra uma
  propriedade real.
- O caminho de escrita real (`dry_run=False` de verdade) nunca gravou nada
  no Cloudbeds de fato, só foi exercitado com a chamada de rede mockada.

## Sessão 2026-07-22 (parte 1) — construção inicial

### O que foi validado de verdade nesta sessão

- **Lógica de match de hóspede** (`core/matching.py`): 8 testes automatizados cobrindo normalização de nome/acento, empate de homônimos, desempate por segundo dado, e o caso de dois candidatos idênticos (nunca decide sozinho). Todos passando.
- **Lógica de histórico de estadias** (`core/history.py`): 4 testes cobrindo contagem por e-mail/telefone, exclusão da reserva atual, e texto da nota gerada. Todos passando.
- **Lógica de grade de ocupação** (`core/occupancy.py`): 4 testes cobrindo quarto ocupado, dia de check-out (não conta como ocupado), reserva cancelada (ignorada), quarto fora da lista da propriedade. Todos passando.
- **Lint** (`ruff check .`): limpo, zero avisos.
- **Sintaxe de todos os arquivos** (`py_compile`) e **boot real do servidor Streamlit** (`streamlit run app.py`, HTTP 200 na home) confirmados nesta máquina.

### Aviso técnico (resolvido na parte 2)

O drive **C:** da máquina estava com **~67 MB livres** durante a primeira parte desta
sessão — causou `MemoryError` intermitente e impediu instalar o Playwright. Foi
liberado espaço (ver acima) e o problema não voltou a ocorrer.

## Pendente (decisões do usuário, não técnicas)

- [ ] Gerar a API key do Cloudbeds com os escopos corretos e preencher `.env`.
- [ ] Criar a service account do Google Cloud, compartilhar a planilha com o e-mail dela, e preencher `GOOGLE_SHEETS_CREDENTIALS_PATH` / `GOOGLE_SHEET_ID`.
- [ ] Confirmar com uma chamada de teste real quais são os nomes de campo do hóspede na propriedade (ajustar `FIELD_MAPPING` no `.env` se precisar).
- [ ] Rodar em modo dry-run com dados reais por um tempo antes de desligar o modo teste.
