# PROJETO.md — Automação Recepção Cloudbeds

## 1. Visão Geral

Sistema local (rodando no seu PC, via Streamlit) com 3 funcionalidades, todas usando a API oficial do Cloudbeds — nunca simula clique na tela deles, então não tem risco de "clicar errado".

| # | Funcionalidade | Tipo de operação |
|---|---|---|
| 1 | Planilha de ocupação (7 dias) | Só LEITURA |
| 2 | Autopreenchimento de hóspede | LEITURA (Sheets) + ESCRITA (só em campos do hóspede) |
| 3 | Histórico de estadias na nota | LEITURA (reservas) + ESCRITA (só no campo da nota) |

**Regra de ouro que vale pro projeto inteiro: o sistema nunca faz DELETE em nada.** Nenhuma das 3 funções usa endpoint de exclusão. Isso já elimina o pior cenário (apagar reserva).

---

## 2. Como funciona o "match" de hóspede

1. Você digita/seleciona o hóspede dentro do Cloudbeds (na reserva, ao inserir os dados)
2. O script pega esse nome e busca na planilha do Google Sheets
3. Ele compara o nome digitado com a coluna de nomes da planilha

### Ponto de atenção
Casar só pelo nome puro é arriscado — dois hóspedes podem se chamar "Maria Silva", ou o nome pode estar com acento diferente, abreviado, etc. Se der match errado, pode inserir dado do hóspede errado na reserva certa.

### Como evitar
- Normalizar o nome antes de comparar (tirar acento, minúsculo, remover espaço duplo)
- Usar um segundo dado da planilha (CPF, telefone, e-mail, data de nascimento) como segunda checagem — só insere automático se nome E esse segundo dado baterem
- Se achar mais de um nome parecido, o sistema NÃO decide sozinho — mostra as opções na tela pra escolha manual
- Se não achar nenhum, avisa "não encontrado" e não faz nada

---

## 3. Regras de segurança (o que o sistema NUNCA faz)

- Nunca deleta reserva, hóspede ou qualquer registro
- Nunca sobrescreve um campo já preenchido manualmente sem mostrar antes o que vai mudar
- Nunca cria uma reserva nova sozinho — só complementa dados de uma reserva/hóspede que já existe/foi selecionado no Cloudbeds
- Nunca faz mudança em lote sem confirmação — mesmo aplicando pra todos os hóspedes de uma reserva, mostra a lista antes de gravar
- Nunca guarda a API key no código — fica em variável de ambiente separada

## 4. O que o sistema SEMPRE faz antes de escrever

1. Lê primeiro, escreve depois — mostra "de: X → para: Y" antes de confirmar
2. Pede confirmação na tela (botão "Confirmar alteração") antes de qualquer escrita real
3. Gera log de tudo que foi alterado (`log.txt`): o quê, quando, reserva/hóspede afetado
4. Roda primeiro em modo teste (dry-run) — só mostra o que faria, sem gravar, até validação total

---

## 5. Arquitetura técnica

[Você] → App Streamlit (localhost)
│
├── Função 1: Cloudbeds API (GET reservas) → gera Excel
├── Função 2: Google Sheets API (leitura) + Cloudbeds API (GET+PUT hóspede)
└── Função 3: Cloudbeds API (GET reservas/hóspedes) → conta estadias → Cloudbeds API (PUT nota)


- **Cloudbeds**: API oficial. Escopos necessários: Reserva (Ler), Hóspede (Ler/Escreva), Campos Personalizados (Ler/Escreva), Data Insights Occupancy (Ler), Acomodação (Ler)
- **Google Sheets**: acesso via `gspread` + credencial de service account do Google (só leitura)
- **Local**: tudo roda no seu PC/rede do hotel, sem servidor externo

---

## 6. Ordem de construção sugerida

1. **Função 1** (ocupação, só leitura) — zero risco, praticamente pronta
2. **Função 3** (histórico) — leitura pesada, escrita simples (1 campo só)
3. **Função 2** (autopreenchimento) — a mais delicada por causa do match de nome — construir por último, com mais testes

---

## 7. Status atual

- [ ] API key do Cloudbeds gerada
- [ ] Escopos configurados (Reserva, Hóspede, Campos Personalizados, Data Insights Occupancy, Acomodação)
- [ ] Função 1 (ocupação) implementada
- [ ] Função 3 (histórico) implementada
- [ ] Função 2 (autopreenchimento) implementada
- [ ] Modo dry-run testado e validado
- [ ] Sistema liberado pra uso "de verdade" (sem confirmação manual)