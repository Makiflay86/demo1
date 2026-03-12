# Plugin de configuración para Claude Code

Plantilla reutilizable con convenciones de código y hooks preconfigurados para proyectos Python + FastAPI con Claude Code.

## Contenido

```
plugin/
├── CLAUDE.md              # Instrucciones base para Claude (con placeholders)
└── .claude/
    └── settings.json      # Hooks: formato automático con black + notificaciones macOS
```

## Hooks incluidos

| Evento | Acción |
|--------|--------|
| `PostToolUse` (Edit/Write sobre `.py`) | Ejecuta `black` sobre el archivo modificado |
| `Notification` | Muestra notificación macOS cuando Claude necesita atención |

## Instalación

### 1. Copiar los archivos al nuevo proyecto

Desde la raíz del nuevo proyecto:

```bash
# Copiar CLAUDE.md
cp ruta/al/plugin/CLAUDE.md .

# Copiar hooks de Claude
cp -r ruta/al/plugin/.claude .
```

O clonando este repositorio y copiando la carpeta `plugin/`:

```bash
cp -r demo1/plugin/.claude /ruta/a/tu-proyecto/
cp demo1/plugin/CLAUDE.md /ruta/a/tu-proyecto/
```

### 2. Personalizar CLAUDE.md

Edita el `CLAUDE.md` copiado y rellena las secciones marcadas con `<!-- ... -->` y `[NOMBRE DEL PROYECTO]`:

- **Descripción**: stack, puerto, propósito del proyecto
- **Arquitectura**: diagrama o descripción del flujo
- **Estructura de archivos**: árbol de archivos relevantes
- **Modelos de datos**: entidades principales
- **Endpoints**: rutas de la API
- **Comandos**: cómo instalar, arrancar y testear

El resto de secciones (idioma, convenciones, lo que NO hacer) aplican tal cual a cualquier proyecto.

### 3. Verificar que `black` está instalado

El hook de formato automático requiere `black` en el entorno del proyecto:

```bash
./venv/bin/pip install black
# o globalmente:
pip install black
```

Si no usas `black`, elimina o ajusta el bloque `PostToolUse` en `.claude/settings.json`.

### 4. Verificar permisos del hook

Claude Code pedirá confirmación la primera vez que ejecute cada hook. Acepta o configura `"alwaysAllow"` en `.claude/settings.json` si quieres que se ejecute sin confirmación:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "FILE=$(jq -r '.tool_input.file_path // empty'); case \"$FILE\" in *.py) black \"$FILE\";; esac"
          }
        ]
      }
    ]
  }
}
```

## Convenciones incluidas en CLAUDE.md

- **Idioma**: todo el código en español (variables, funciones, comentarios, tests, mensajes de error)
- **Python**: PEP 8, validación en Pydantic, errores HTTP en español
- **Tests**: independientes, nombres descriptivos, sin mocks de internals
- **JavaScript**: función centralizada para fetch, sin frameworks por defecto
- **CSS**: variables en `:root`, animaciones en `@keyframes`

## Requisitos del sistema

- macOS (para el hook de notificaciones con `osascript`). En Linux/Windows, elimina o adapta el bloque `Notification` en `.claude/settings.json`.
- `jq` instalado (`brew install jq` en macOS).
- `black` instalado en el entorno Python del proyecto.
