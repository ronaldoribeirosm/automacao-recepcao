# PROGRESSO.md

## Sessão 2026-07-22 — construção inicial

### O que foi validado de verdade nesta sessão

- **Lógica de match de hóspede** (`core/matching.py`): 8 testes automatizados cobrindo normalização de nome/acento, empate de homônimos, desempate por segundo dado, e o caso de dois candidatos idênticos (nunca decide sozinho). Todos passando.
- **Lógica de histórico de estadias** (`core/history.py`): 4 testes cobrindo contagem por e-mail/telefone, exclusão da reserva atual, e texto da nota gerada. Todos passando.
- **Lógica de grade de ocupação** (`core/occupancy.py`): 4 testes cobrindo quarto ocupado, dia de check-out (não conta como ocupado), reserva cancelada (ignorada), quarto fora da lista da propriedade. Todos passando.
- **Lint** (`ruff check .`): limpo, zero avisos.
- **Sintaxe de todos os arquivos** (`py_compile`) e **boot real do servidor Streamlit** (`streamlit run app.py`, HTTP 200 na home) confirmados nesta máquina.

### O que NÃO foi validado (pendente)

- **Nenhuma chamada real à API do Cloudbeds foi feita** — não havia API key disponível nesta sessão. Os nomes de endpoint (`getReservations`, `getReservation`, `putGuest`, `getCustomFields`, `getReservationNotes`, `postReservationNote`, `getRooms`) foram confirmados via documentação pública da Cloudbeds, mas os **nomes exatos dos campos de hóspede** (`guestCPF`, `guestPhone1`, `guestBirthdate`, etc., em `core/config.py` → `DEFAULT_FIELD_MAPPING`) são um ponto de partida e precisam ser confirmados com uma chamada de teste real antes de usar em produção — podem ser campos personalizados com nomes diferentes na propriedade específica.
- **Nenhuma leitura real do Google Sheets foi feita** — sem credencial de service account disponível nesta sessão.
- **Interface nunca foi aberta num navegador de verdade** — o boot do servidor foi confirmado via HTTP (curl), mas a instalação do Playwright (pra tirar screenshot e checar erros de renderização) falhou por falta de espaço em disco na máquina (ver aviso abaixo). As três páginas (`pages/1_Ocupacao.py`, `2_Autopreenchimento.py`, `3_Historico.py`) foram revisadas por leitura e passam no `py_compile`, mas o fluxo de clique real (buscar reserva → ver diff → confirmar) nunca rodou contra dados reais.
- **Modo produção (dry-run desligado) nunca foi exercitado** — por não haver credenciais, todo o caminho de escrita real (`put_guest`, `post_reservation_note` com `dry_run=False`) só foi revisado por leitura de código, não executado.

### Aviso técnico importante (fora do escopo deste projeto)

O drive **C:** da máquina estava com **~67 MB livres** durante esta sessão — isso causou `MemoryError` intermitente do Python (provavelmente por falta de espaço pro arquivo de paginação do Windows crescer) e impediu a instalação do Chromium do Playwright. Vale liberar espaço em C: antes da próxima sessão de desenvolvimento, ou os problemas podem se repetir (e afetar outras coisas na máquina, não só este projeto).

## Pendente (decisões do usuário, não técnicas)

- [ ] Gerar a API key do Cloudbeds com os escopos corretos e preencher `.env`.
- [ ] Criar a service account do Google Cloud, compartilhar a planilha com o e-mail dela, e preencher `GOOGLE_SHEETS_CREDENTIALS_PATH` / `GOOGLE_SHEET_ID`.
- [ ] Confirmar com uma chamada de teste real quais são os nomes de campo do hóspede na propriedade (ajustar `FIELD_MAPPING` no `.env` se precisar).
- [ ] Rodar em modo dry-run com dados reais por um tempo antes de desligar o modo teste.
- [ ] Liberar espaço em disco em C: (ver aviso acima).
