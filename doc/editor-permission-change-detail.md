# Detalle técnico de cambios para habilitar Editor

Este documento lista los archivos modificados para habilitar el rol `editor`, qué código cambió y por qué.

## Resumen

Se tocaron dos áreas:

1. **Backend**: decidir cuándo un push puede usar permiso `Edit` en vez de `Upload`.
2. **Frontend**: dejar de ocultar la opción `Editor` en los dropdowns.

También se agregaron documentos de apoyo.

## Commits relacionados

| Commit | Descripción |
|---|---|
| `c023c735` | Backend y tests de clasificación Editor/Writer. |
| `bfa644f8` | UI y documentación base. |

## Archivos con cambios de código

### `server/mergin/sync/project_handler.py`

#### Antes

`get_push_permission(changes)` devolvía siempre:

```python
return ProjectPermissions.Upload
```

Eso significaba que cualquier push requería permiso de **Writer**.

#### Ahora

Se agregó clasificación conservadora:

```python
if not changes or not self._editor_safe_changes(changes):
    return ProjectPermissions.Upload
return ProjectPermissions.Edit
```

#### Nuevas piezas agregadas

| Elemento | Función |
|---|---|
| `PROTECTED_EDITOR_FILES = {"mergin-config.json"}` | Lista archivos que Editor nunca debe tocar. |
| `_editor_safe_changes(changes)` | Evalúa si todo el payload puede pasar como Editor. |
| `_editor_safe_added_file(item)` | Decide si un archivo agregado es permitido para Editor. |
| `_editor_safe_updated_file(item)` | Decide si un archivo actualizado es permitido para Editor. |
| `_is_protected_file(path)` | Detecta `.qgs`, `.qgz` y `mergin-config.json`. |

#### Regla implementada

| Cambio recibido | Resultado |
|---|---|
| Sin cambios reales | Writer |
| Agregar archivo común | Editor |
| Actualizar archivo común | Editor |
| Actualizar `.gpkg` / `.sqlite` con `diff` | Editor |
| Agregar `.gpkg` / `.sqlite` | Writer |
| Actualizar `.gpkg` / `.sqlite` sin `diff` | Writer |
| Borrar cualquier archivo | Writer |
| Tocar `.qgs`, `.qgz`, `mergin-config.json` | Writer |
| Path vacío/desconocido | Writer |

#### Intención

Permitir que Editor sincronice cambios de campo sin darle permisos de estructura del proyecto.

---

### `server/mergin/tests/test_project_handler.py`

#### Antes

Sólo había un test que verificaba que:

```python
ProjectHandler().get_push_permission(None) == ProjectPermissions.Upload
```

#### Ahora

Se agregó un test parametrizado:

```python
test_project_push_permission_for_editor_safe_changes
```

#### Casos cubiertos

| Caso | Esperado |
|---|---|
| `changes = None` | Writer |
| Sin cambios reales | Writer |
| Agregar `photos/photo.jpg` | Editor |
| Agregar item sin `path` | Writer |
| Agregar `data/new_layer.gpkg` | Writer |
| Agregar `survey.qgs` | Writer |
| Agregar `mergin-config.json` | Writer |
| Actualizar `data/base.gpkg` con `diff` | Editor |
| Actualizar `data/base.gpkg` sin `diff` | Writer |
| Actualizar `survey.qgz` | Writer |
| Borrar `photos/photo.jpg` | Writer |

#### Intención

Proteger la regla de seguridad: ante duda o cambio estructural, exigir Writer.

---

### `web-app/packages/app/src/App.vue`

#### Antes

El dashboard normal ocultaba `editor` con:

```ts
const projectStore = useProjectStore()
projectStore.filterPermissions(['editor'], ['edit'])
```

También importaba `useProjectStore`.

#### Ahora

Se eliminó:

```ts
useProjectStore
const projectStore = useProjectStore()
projectStore.filterPermissions(['editor'], ['edit'])
```

#### Intención

Dejar que `Editor` aparezca en las opciones de permisos del dashboard normal.

---

### `web-app/packages/admin-app/src/App.vue`

#### Antes

El admin app también ocultaba `editor` con:

```ts
const projectStore = useProjectStore()
projectStore.filterPermissions(['editor'], ['edit'])
```

También importaba `useProjectStore`.

#### Ahora

Se eliminó:

```ts
useProjectStore
const projectStore = useProjectStore()
projectStore.filterPermissions(['editor'], ['edit'])
```

#### Intención

Dejar que `Editor` aparezca en las opciones de permisos del panel admin.

## Archivos de documentación agregados

### `doc/editor-permission-map.md`

Documento previo de análisis.

Incluye:

- estado actual del rol `editor`;
- archivos donde ya existía soporte parcial;
- reglas recomendadas;
- riesgos;
- tests necesarios.

### `doc/editor-permission-audit-brief.md`

Brief para que otra IA audite el cambio.

Incluye:

- commits a revisar;
- archivos tocados;
- preguntas de auditoría;
- comandos sugeridos;
- riesgo principal.

### `doc/editor-permission-change-detail.md`

Este documento.

Incluye:

- detalle de cada archivo cambiado;
- código removido o agregado;
- intención de cada cambio.

## Verificación realizada

Se ejecutó:

```bash
python -m py_compile server/mergin/sync/project_handler.py server/mergin/tests/test_project_handler.py
```

Resultado: pasó.

No se pudo ejecutar:

```bash
python -m pytest server/mergin/tests/test_project_handler.py -q
```

Motivo: el Python disponible no tenía `pytest`.

No se pudo ejecutar validación frontend con Yarn porque `yarn` no estaba disponible.

## Punto importante

Esto no garantiza 100% ausencia de errores. El cambio es conservador, pero todavía necesita validación en entorno real con:

- backend tests;
- frontend build/lint;
- prueba funcional con usuario `editor`;
- prueba funcional con usuario `writer`;
- prueba negativa intentando subir `.qgs`, `.qgz`, `mergin-config.json` y `.gpkg` sin diff.

