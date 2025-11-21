# Guia de Contribuição

Obrigado por considerar contribuir para o Poker Game! 🎉

## Como Contribuir

### Reportar Bugs

Se você encontrou um bug:

1. Verifique se já não existe uma [issue](https://github.com/crsthn-slv/poker-game/issues) sobre o problema
2. Se não existir, crie uma nova issue com:
   - Descrição clara do problema
   - Passos para reproduzir
   - Comportamento esperado vs comportamento atual
   - Screenshots (se aplicável)
   - Informações do ambiente (OS, Python version, etc)

### Sugerir Melhorias

1. Verifique se já não existe uma issue sobre a melhoria
2. Crie uma nova issue com:
   - Descrição clara da melhoria
   - Casos de uso
   - Benefícios esperados

### Contribuir com Código

1. **Fork o repositório**
2. **Crie uma branch para sua feature:**
   ```bash
   git checkout -b feature/minha-feature
   ```

3. **Faça suas alterações:**
   - Siga o estilo de código existente
   - Adicione comentários quando necessário
   - Mantenha commits pequenos e descritivos

4. **Teste suas alterações:**
   ```bash
   python3 -m pytest tests/
   ```

5. **Commit suas mudanças:**
   ```bash
   git commit -m "feat: adiciona nova funcionalidade X"
   ```
   
   Use prefixos convencionais:
   - `feat:` para novas funcionalidades
   - `fix:` para correções de bugs
   - `docs:` para documentação
   - `style:` para formatação
   - `refactor:` para refatoração
   - `test:` para testes
   - `chore:` para tarefas de manutenção

6. **Push para sua branch:**
   ```bash
   git push origin feature/minha-feature
   ```

7. **Abra um Pull Request:**
   - Descreva claramente o que foi feito
   - Referencie issues relacionadas (ex: "Fixes #123")
   - Adicione screenshots se aplicável

## Padrões de Código

### Python

- Siga [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use type hints quando possível
- Documente funções e classes com docstrings
- Mantenha funções pequenas e focadas

### JavaScript

- Use `const` e `let` (evite `var`)
- Use arrow functions quando apropriado
- Mantenha funções pequenas e focadas
- Comente código complexo

### Commits

- Use mensagens descritivas
- Uma funcionalidade por commit
- Referencie issues quando aplicável

## Estrutura de Testes

Adicione testes para novas funcionalidades:

```python
# tests/test_nova_feature.py
def test_nova_funcionalidade():
    # Arrange
    # Act
    # Assert
    pass
```

## Perguntas?

Se tiver dúvidas, abra uma issue ou entre em contato!

Obrigado por contribuir! 🚀

