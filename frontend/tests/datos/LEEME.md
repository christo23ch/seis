# Datos de prueba del frontend

Salida REAL del motor, generada sin base de datos, para probar la presentación contra lo que
el motor emite de verdad y no contra un texto inventado:

| Fichero | Caso |
|---|---|
| `informe_caso19.md`, `resultado_caso19.json` | Caso dorado §19 (`backend/tests/test_golden_caso19.py::entrada_caso_19`) |
| `resultado_rentista.json` | El §19 con perfil rentista e hipoteca: alquiler 950 €/mes, IBI 350 €, comunidad 60 €/mes; LTV 70 %, 3,5 % |
| `resultado_dos_tramos.json` | El §19 con valor de referencia del Catastro de 150.000 €: base imponible mínima, tramo fiscal «bajo» |

Si el motor cambia el informe o el resultado, se regeneran desde `backend/` con:

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "
import json, sys; sys.path.insert(0, '.')
from tests.test_golden_caso19 import entrada_caso_19
from app.engine.pipeline import ejecutar_analisis
from app.engine.contracts import RentistaInput, FinanciacionInput, CostesInput
D = '../frontend/tests/datos/'
def guardar(nombre, r, md=False):
    d = r.model_dump(mode='json'); m = d.pop('informe_markdown')
    open(D + f'resultado_{nombre}.json', 'w', encoding='utf-8', newline='\n').write(json.dumps(d, ensure_ascii=False, indent=1))
    if md: open(D + f'informe_{nombre}.md', 'w', encoding='utf-8', newline='\n').write(m)
e = entrada_caso_19()
guardar('caso19', ejecutar_analisis(e), md=True)
guardar('rentista', ejecutar_analisis(e.model_copy(update={'perfil': 'rentista',
    'rentista': RentistaInput(renta_mensual_estimada=950, ibi_anual=350, comunidad_mensual=60),
    'financiacion': FinanciacionInput(tipo='hipoteca', preaprobada=True, ltv=0.7, interes_anual_pct=3.5)})))
guardar('dos_tramos', ejecutar_analisis(e.model_copy(update={'costes': CostesInput(
    **{**e.costes.model_dump(), 'valor_referencia_catastral': 150000})})))
"
```

Generados el 2026-10-07 con el motor de la Fase 5J-3.
