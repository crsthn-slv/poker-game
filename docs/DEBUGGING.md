# Guia de Debugging - Poker Game

Este documento fornece um guia completo para identificar e resolver problemas comuns no jogo de poker.

## Índice

1. [Como Identificar Erros de Serialização](#como-identificar-erros-de-serialização)
2. [Como Ativar Modo Debug](#como-ativar-modo-debug)
3. [Checklist de Problemas Comuns](#checklist-de-problemas-comuns)
4. [Como Testar Manualmente](#como-testar-manualmente)
5. [Logs e Mensagens de Erro](#logs-e-mensagens-de-erro)

## Como Identificar Erros de Serialização

### Erro: `'dict' object has no attribute '__dict__'`

**Causa**: O código tentou acessar `__dict__` em um objeto que já é um dicionário.

**Solução**: Já corrigido! O código agora verifica o tipo antes de serializar.

**Como verificar**:
- Verifique os logs do servidor para mensagens de erro
- Procure por mensagens que mencionam "Erro ao serializar" ou "Erro crítico em receive_round_result_message"

### Erro: `Cannot read properties of undefined (reading 'uuid')`

**Causa**: Tentativa de acessar propriedade de objeto undefined/null no frontend.

**Solução**: Já corrigido! O código agora valida objetos antes de acessar propriedades.

**Como verificar**:
- Abra o console do navegador (F12)
- Procure por erros JavaScript relacionados a propriedades undefined

## Como Ativar Modo Debug

### Backend (Python)

Defina a variável de ambiente `POKER_DEBUG`:

```bash
export POKER_DEBUG=true
python3 web/server.py
```

Ou no Windows:
```cmd
set POKER_DEBUG=true
python web\server.py
```

**O que o modo debug faz**:
- Mostra logs detalhados de todas as operações
- Exibe stack traces completos de erros
- Loga tipos de objetos e valores durante serialização

### Frontend (JavaScript)

Edite `web/js/game.js` e altere:

```javascript
const DEBUG_MODE = true; // Mude de false para true
```

**O que o modo debug faz**:
- Mostra logs no console do navegador
- Exibe informações sobre validações de dados
- Loga erros com mais detalhes

## Checklist de Problemas Comuns

### 1. Erro de Serialização JSON

**Sintomas**:
- Erro no console: "Erro ao parsear resposta JSON"
- Jogo para de responder
- Mensagens de erro no servidor

**Verificações**:
- [ ] Verifique se o servidor está rodando
- [ ] Verifique os logs do servidor para erros de serialização
- [ ] Ative o modo debug para ver mais detalhes
- [ ] Verifique se `hand_info` ou `winners` têm formato inesperado

**Solução**:
- O código já trata diferentes formatos automaticamente
- Se o problema persistir, verifique os logs para identificar o formato específico

### 2. Erro de Propriedades Undefined no Frontend

**Sintomas**:
- Erro no console: "Cannot read properties of undefined"
- Interface não atualiza corretamente
- Botões não funcionam

**Verificações**:
- [ ] Abra o console do navegador (F12)
- [ ] Verifique se há erros JavaScript
- [ ] Ative o modo debug no frontend
- [ ] Verifique se `gameState` está sendo recebido corretamente

**Solução**:
- O código agora valida todos os dados antes de acessar propriedades
- Verifique a resposta da API `/api/game_state` no Network tab

### 3. Jogo Não Inicia

**Sintomas**:
- Botão de iniciar não funciona
- Erro ao tentar começar jogo
- Servidor retorna erro 500

**Verificações**:
- [ ] Verifique se todas as dependências estão instaladas: `make install` ou `pip install -r requirements.txt`
- [ ] Verifique se o servidor está rodando na porta 5000
- [ ] Verifique os logs do servidor
- [ ] Verifique se há bots suficientes disponíveis

**Solução**:
- Reinicie o servidor
- Verifique se não há outro processo usando a porta 5000
- Limpe o cache do navegador

### 4. Ações do Jogador Não São Processadas

**Sintomas**:
- Botões de ação não respondem
- Jogo fica travado esperando ação
- Erro ao enviar ação

**Verificações**:
- [ ] Verifique o console do navegador para erros
- [ ] Verifique a resposta da API `/api/player_action`
- [ ] Verifique se `web_player` está inicializado corretamente
- [ ] Verifique os logs do servidor

**Solução**:
- Recarregue a página
- Reinicie o jogo
- Verifique se a ação é válida (fold, call, raise)

## Como Testar Manualmente

### 1. Testar Serialização

Execute os testes unitários:

**Com Makefile:**
```bash
make test
```

**Ou manualmente:**
```bash
cd /caminho/para/poker_test
python3 -m pytest tests/test_serialization.py -v
```

### 2. Testar Fluxo Completo

Execute os testes de fluxo:

**Com Makefile:**
```bash
make test
```

**Ou manualmente:**
```bash
python3 -m pytest tests/test_game_flow.py -v
```

### 3. Testar no Navegador

1. Inicie o servidor:

   **Com Makefile:**
   ```bash
   make run-server
   ```

   **Ou manualmente:**
   ```bash
   cd web
   python3 server.py
   ```

2. Abra o navegador em `http://localhost:5002` (ou porta configurada)

3. Abra o console do navegador (F12)

4. Configure seu nome e inicie o jogo

5. Monitore o console para erros

6. Verifique a aba Network para ver as requisições da API

### 4. Testar com Modo Debug

1. Ative o modo debug no backend:

   **Com Makefile:**
   ```bash
   export POKER_DEBUG=true
   make run-server
   ```

   **Ou manualmente:**
   ```bash
   export POKER_DEBUG=true
   python3 web/server.py
   ```

2. Para o jogo console:
   ```bash
   export POKER_DEBUG=true
   make run-console
   ```

3. Ative o modo debug no frontend (edite `game.js`)

4. Execute o jogo e monitore os logs

## Logs e Mensagens de Erro

### Backend

Os logs do backend aparecem no terminal onde o servidor está rodando.

**Formato dos logs**:
```
[YYYY-MM-DD HH:MM:SS] ERROR: Mensagem | Context: {...} | Error: ...
[YYYY-MM-DD HH:MM:SS] DEBUG: Mensagem | Data: {...}
```

**Logs importantes**:
- `Erro ao serializar seat`: Problema ao processar informações de um jogador
- `Erro crítico em receive_round_result_message`: Erro ao processar fim de round
- `Erro em receive_game_update_message`: Erro ao processar ação de jogador

### Frontend

Os logs do frontend aparecem no console do navegador (F12).

**Formato dos logs**:
```
[ISO_TIMESTAMP] DEBUG: Mensagem Data: {...}
Erro em função: ...
```

**Logs importantes**:
- `gameState inválido`: Resposta da API não é válida
- `round inválido`: Dados do round estão corrompidos
- `Erro ao atualizar...`: Problema ao atualizar interface

## Resolução Rápida de Problemas

### Problema: Erro de serialização

1. Ative o modo debug
2. Verifique os logs para identificar o tipo de objeto problemático
3. O código já trata automaticamente, mas se persistir, verifique os testes

### Problema: Interface não atualiza

1. Verifique o console do navegador
2. Verifique a aba Network para ver se as requisições estão sendo feitas
3. Verifique se o servidor está respondendo corretamente

### Problema: Jogo trava

1. Verifique os logs do servidor
2. Verifique se há erros no console do navegador
3. Tente reiniciar o jogo
4. Limpe o cache do navegador

## Executando Testes

**Com Makefile (Recomendado):**
```bash
# Todos os testes
make test

# Teste com cobertura
make test-cov
```

**Ou manualmente:**
```bash
# Todos os testes
python3 -m pytest tests/ -v

# Teste específico
python3 -m pytest tests/test_serialization.py -v
python3 -m pytest tests/test_game_flow.py -v
```

**Nota:** O Makefile detecta automaticamente o Python correto (com pokerkit instalado) para executar os testes.

## Contato e Suporte

Se encontrar problemas não cobertos neste guia:

1. Ative o modo debug
2. Colete os logs (backend e frontend)
3. Execute os testes e verifique se passam
4. Documente o problema com:
   - Mensagem de erro completa
   - Stack trace (se disponível)
   - Passos para reproduzir
   - Logs relevantes

## Melhorias Futuras

- Adicionar mais testes automatizados
- Implementar sistema de métricas
- Adicionar dashboard de monitoramento
- Melhorar mensagens de erro para usuários finais

