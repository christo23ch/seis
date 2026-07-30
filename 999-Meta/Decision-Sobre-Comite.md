---
tipo: meta
---

# Decisión: no existe carpeta "Comité"

Se evaluó crear `50-Comite/` o similar tras una petición explícita de auditoría que la mencionaba. Se descarta por el mismo principio de la Fase 1 de la implantación original: **no duplicar lo que ya tiene un lugar**.

Las revisiones "de comité" de este proyecto no son una entidad organizativa separada con vida propia — son auditorías con un rol de auditor distinto cada vez (`Security Lead`, `Release Committee`, `Staff Engineer`...). Ese rol ya es un campo de frontmatter (`rol_auditor`) en cada nota de `60-Auditorias/`, consultable con:

```dataview
TABLE rol_auditor, veredicto
FROM #tipo/auditoria
```

Crear una carpeta `Comité` aparte solo introduciría una segunda forma de encontrar lo mismo que ya devuelve esta consulta.
