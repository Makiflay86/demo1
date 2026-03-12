# CLAUDE.md — [NOMBRE DEL PROYECTO]

## Idioma

**El idioma principal y único de este proyecto es el español.**

- Todo el código nuevo (nombres de variables, funciones, clases, comentarios, docstrings, mensajes de error, tests) debe escribirse en español.
- Las únicas excepciones permitidas son palabras técnicas sin traducción natural: `id`, `status`, `endpoint`, `commit`, `query`, nombres de librerías externas y similares.
- Si Claude genera código en inglés sin que se le pida explícitamente, es un error.

---

## Descripción

<!-- Describe aquí el propósito del proyecto, stack y puerto si aplica. -->

---

## Arquitectura

<!-- Diagrama o descripción de la arquitectura del sistema. -->

---

## Estructura de archivos

<!-- Árbol de archivos relevantes con descripción de cada uno. -->

---

## Modelos de datos

<!-- Tablas o descripciones de los modelos principales. -->

---

## Endpoints de la API

<!-- Documenta cada endpoint: método, ruta, body, respuestas. -->

---

## Comandos

### Instalar dependencias

```bash
# Ejemplo:
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

### Arrancar el servidor

```bash
# Ejemplo:
./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Ejecutar tests

```bash
./venv/bin/pytest tests/ -v
```

---

## Convenciones de código

### General
- **Idioma: español** en todo lo que se escriba (ver sección Idioma arriba).
- Sin comentarios obvios. Solo comentar lo que no es evidente.
- No añadir docstrings a funciones simples. Solo donde la lógica lo justifique.
- No sobre-ingeniería: si algo se usa una sola vez, no abstraerlo.

### Python (backend)
- Formato: [PEP 8](https://peps.python.org/pep-0008/). Indentación de 4 espacios.
- Toda validación de entrada se hace en los schemas Pydantic, no en los endpoints.
- Los endpoints no hacen lógica de negocio compleja: delegan en la capa de datos.
- Los errores HTTP se lanzan con `raise HTTPException(código, "mensaje en español")`.

### Tests
- Cada test es independiente: no depende del orden de ejecución ni del estado de otro test.
- Los nombres de los tests describen qué se verifica: `test_crear_usuario_duplicado_devuelve_400`.
- No mockear internals del framework — usar la pila real con BD en memoria.

### JavaScript (frontend)
- Vanilla JS salvo que el proyecto indique otro framework.
- Todas las llamadas HTTP pasan por una función centralizada — nunca usar `fetch` directamente.

### CSS
- Variables de color definidas en `:root` — nunca usar valores de color hardcodeados fuera de `:root`.
- Las animaciones van en bloques `@keyframes` al final de su sección.

---

## Lo que NO hacer

- No commitear bases de datos ni entornos virtuales.
- No añadir endpoints que no tengan su test correspondiente.
- No escribir código, comentarios ni mensajes en inglés.
