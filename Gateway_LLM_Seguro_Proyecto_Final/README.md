# Gateway LLM Seguro

Proyecto final desarrollado con FastAPI para centralizar las llamadas hacia un proveedor LLM y aplicar controles de seguridad antes y después de cada solicitud.

## Controles implementados

- LLM01: validación de entrada contra patrones de Prompt Injection.
- LLM02: credenciales por variables de entorno y logs sin datos sensibles.
- LLM10: rate limiting por cliente autenticado.
- LLM07: validación de la respuesta para detectar fuga del system prompt.

## Estructura principal

```text
app/
  main.py
  config.py
  dependencies.py
  logging_config.py
  models.py
  providers/
  security/
tests/
docs/OWASP_MAPPING.md
scripts/demo.ps1
```

## Ejecución

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

Swagger:

```text
http://localhost:8000/docs
```

## Prueba rápida

```powershell
$Headers = @{ "X-Gateway-Key" = "change-me-client-key" }

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/v1/chat" `
  -Headers $Headers `
  -ContentType "application/json" `
  -Body '{"message":"Explica qué es un gateway LLM"}'
```

También se puede usar:

```powershell
.\scripts\demo.ps1
```

## Pruebas automatizadas

```powershell
pytest -q
```

## Demostración antes y después

Para mostrar la línea base sin controles:

```env
SECURITY_ENABLED=false
```

Para activar los controles:

```env
SECURITY_ENABLED=true
```

Para probar la fuga simulada del system prompt:

```env
LLM_PROVIDER=mock
MOCK_LEAK_MODE=true
```

El detalle de las evidencias está en `docs/OWASP_MAPPING.md`.
