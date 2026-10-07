# Datos de prueba del frontend

`informe_caso19.md` y `resultado_caso19.json` son la salida REAL del motor para el caso
dorado §19 (`backend/tests/test_golden_caso19.py::entrada_caso_19`), generada sin base de
datos. Los usan los tests de vitest para probar la presentación contra lo que el motor
emite de verdad, no contra un texto inventado.

Si el motor cambia el informe o el resultado, se regeneran desde `backend/` con:

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "
import json, sys; sys.path.insert(0, '.')
from tests.test_golden_caso19 import entrada_caso_19
from app.engine.pipeline import ejecutar_analisis
r = ejecutar_analisis(entrada_caso_19())
open('../frontend/tests/datos/informe_caso19.md', 'w', encoding='utf-8', newline='\n').write(r.informe_markdown)
d = r.model_dump(mode='json'); d.pop('informe_markdown')
open('../frontend/tests/datos/resultado_caso19.json', 'w', encoding='utf-8', newline='\n').write(json.dumps(d, ensure_ascii=False, indent=1))
"
```

Generados el 2026-10-07 con el motor de `main` en `211fed1`.
