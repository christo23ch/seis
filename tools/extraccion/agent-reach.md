# Agent Reach — qué modifica y qué se ha ejecutado

**Repositorio:** <https://github.com/Panniantong/agent-reach> · **Versión:** 1.5.0 · **Commit
revisado e instalado:** `a19a171fa980a0785849596492e0af4db800c82f` (2026-10-06).
**Uso en SEIS:** herramienta de investigación para Claude Code. **No forma parte del
producto**: ni `backend/` ni `frontend/` la importan, y nada de lo que obtenga se ingesta sin
pasar por el ADR-0021.

## Instalación hecha

En un entorno propio e ignorado por git, **fijado al commit revisado** en lugar del `main.zip`
móvil que propone su guía:

```bash
python -m venv tools/extraccion/.venv-agentreach
tools/extraccion/.venv-agentreach/Scripts/python -m pip install \
  "https://github.com/Panniantong/agent-reach/archive/a19a171fa980a0785849596492e0af4db800c82f.zip"
```

Dependencias: requests, feedparser, python-dotenv, loguru, pyyaml, rich, yt-dlp
(`requisitos/agent-reach.txt`). Sin los extras `browser`, `cookies` ni `all`.

## Lo único ejecutado: la comprobación segura

```bash
agent-reach install --env=auto        # sin --system
```

Verificado en el código (`agent_reach/cli.py`, `_cmd_install`) antes de ejecutarlo: sin
`--system`, `Config(read_only=True)`, no crea `~/.agent-reach/`, no instala nada y no copia la
skill. Verificado también después: `~/.claude/skills` sin cambios y siguen sin existir
`~/.agent-reach`, `~/.agents`, `~/.openclaw`, `~/.config/opencode` y `~/.config/yt-dlp`.

Sí hace **peticiones de red de solo lectura** para probar canales: Jina Reader (`r.jina.ai`),
la API pública de V2EX y la de búsqueda de Bilibili. No lee cookies del navegador.

Resultado: **4/16 canales activos** (V2EX, RSS, web vía Jina Reader, búsqueda de Bilibili).
GitHub queda en «[!]» (no ejecuta `gh auth status`, que escribe un identificador de
dispositivo), YouTube en «[X]» (yt-dlp está en el entorno pero no en el PATH) y la búsqueda
semántica Exa en «[X]» (falta `mcporter`).

## Lo que modificaría si se ejecutara con `--system` (NO autorizado)

| Qué | Dónde | Alcance |
|---|---|---|
| Instalar gh CLI y Node.js si faltan | `apt-get` / Homebrew (en Windows no hay instalador automático) | Sistema |
| `npm install -g undici` | Paquetes npm globales | Usuario/sistema |
| `npm install -g mcporter` y registrar el servidor MCP de Exa (`https://mcp.exa.ai/mcp`, `--scope home`) | npm global y configuración de mcporter en el perfil | Usuario |
| Configurar Node.js como intérprete JS de yt-dlp | `~/.config/yt-dlp/config` | Usuario |
| Crear configuración, tokens y herramientas | `~/.agent-reach/` (`config.json`, `tools/`) | Usuario |
| **Copiar su skill** (SKILL.md y referencias) | `~/.claude/skills/agent-reach/` y cualquier otra raíz de skills que exista (`~/.agents`, `~/.openclaw`, `~/.config/opencode`); si no hay ninguna, crea `~/.agents/skills/` | Usuario — **cambiaría el comportamiento de Claude Code en todos los proyectos** |
| Con `--channels=…`: CLIs de terceros (twitter-cli, rdt-cli, bili-cli, OpenCLI, boss-agent-cli…), extensión de Chrome, Chrome con puerto de depuración 9222 | Global | Sistema/usuario |

Y por separado, mediante `agent-reach configure …`: cookies de Twitter, Xiaohongshu, Xueqiu o
Bilibili, proxies y claves de API (Groq). **Nada de esto se ha hecho ni se hará sin
autorización expresa**; las cookies y cuentas de redes sociales quedan fuera de SEIS
(ADR-0021: sin datos personales).

## Observaciones

- Su guía sugiere proxies residenciales para eludir el «风控» (control de riesgos) de las
  plataformas: es evasión anti-bot y está **prohibido** por el ADR-0021.
- Su modo web lee páginas a través de Jina Reader, un tercero: la petición sale desde los
  servidores de Jina, no desde aquí, y ese tercero ve la URL. Para fuentes de SEIS el
  ADR-0021 exige que la ficha de la fuente lo apruebe.
