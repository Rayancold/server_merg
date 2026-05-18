# Auditoría solicitada: habilitación del rol Editor

Este documento es un briefing para que una segunda IA audite los cambios hechos para habilitar el rol `editor` en `server_merg`.

## Respuesta corta para el auditor

No asumir que el cambio es correcto. Verificar especialmente que `editor` no se convierta accidentalmente en `writer`.

El objetivo funcional es:

> `Editor = Reader + add/edit/delete features`, sin permitir cambios estructurales del proyecto.

Fuente oficial: https://merginmaps.com/docs/manage/permissions/

## Commits involucrados

| Commit | Contenido |
|---|---|
| `c023c735` | Backend: clasificación de permisos de push y tests. |
| `bfa644f8` | Frontend/docs: mostrar Editor en UI y documentar mapa. |

## Archivos modificados

| Archivo | Qué cambió | Qué auditar |
|---|---|---|
| `server/mergin/sync/project_handler.py` | `get_push_permission(changes)` ya no devuelve siempre `ProjectPermissions.Upload`; ahora clasifica cambios editor-safe como `ProjectPermissions.Edit`. | Que no permita cambios estructurales por error. |
| `server/mergin/tests/test_project_handler.py` | Tests unitarios para la clasificación Editor vs Writer. | Que los casos cubran lo importante y no sean demasiado optimistas. |
| `web-app/packages/app/src/App.vue` | Se quitó `projectStore.filterPermissions(['editor'], ['edit'])`. | Que Editor aparezca en el dashboard normal sin romper imports. |
| `web-app/packages/admin-app/src/App.vue` | Se quitó `projectStore.filterPermissions(['editor'], ['edit'])`. | Que Editor aparezca en admin sin romper imports. |
| `doc/editor-permission-map.md` | Mapa técnico previo al cambio. | Que coincida con el comportamiento final. |

## Regla implementada actualmente

`ProjectHandler.get_push_permission(changes)` devuelve:

| Caso | Permiso requerido |
|---|---|
| `changes` vacío, nulo o sin cambios reales | `ProjectPermissions.Upload` |
| Agregar archivo no protegido y no versionado | `ProjectPermissions.Edit` |
| Actualizar archivo no protegido y no versionado | `ProjectPermissions.Edit` |
| Actualizar `.gpkg` / `.sqlite` con `diff` | `ProjectPermissions.Edit` |
| Borrar cualquier archivo | `ProjectPermissions.Upload` |
| Agregar `.gpkg` / `.sqlite` | `ProjectPermissions.Upload` |
| Actualizar `.gpkg` / `.sqlite` sin `diff` | `ProjectPermissions.Upload` |
| Agregar/actualizar `.qgs` / `.qgz` | `ProjectPermissions.Upload` |
| Agregar/actualizar `mergin-config.json` | `ProjectPermissions.Upload` |
| Path vacío/desconocido | `ProjectPermissions.Upload` |

## Punto delicado

La implementación actual es **más conservadora** que la documentación oficial:

- La doc indica que Editor puede agregar algunos archivos, incluyendo GeoPackage en ciertos escenarios.
- La implementación actual bloquea agregar `.gpkg` / `.sqlite`.
- La doc permite remover algunos archivos, pero no `.qgs`, `.qgz`, `mergin-config.json` ni `.gpkg`.
- La implementación actual bloquea **todo** removal.

Esto fue intencional para evitar que Editor sea Writer disfrazado. Auditar si ese tradeoff es aceptable.

## Preguntas que la segunda IA debe responder

1. ¿La clasificación de `get_push_permission(changes)` respeta la intención de seguridad?
2. ¿Hay algún camino alternativo de push que no pase por `get_push_permission(changes)`?
3. ¿`upload_chunk()` con `ProjectPermissions.Edit` permite algo peligroso si `create_project_version()` luego exige `Upload` para cambios estructurales?
4. ¿La UI queda coherente con el backend o puede prometer algo que después falle?
5. ¿Los tests agregados son suficientes para los riesgos principales?
6. ¿El cambio debería permitir removals no protegidos para alinearse más con la doc oficial?
7. ¿El cambio debería permitir agregar `.gpkg` sólo si se puede probar que no rompe estructura/proyecto?

## Comandos sugeridos de verificación

Desde la raíz del repo:

```bash
git show --stat c023c735
git show --stat bfa644f8
git show c023c735 -- server/mergin/sync/project_handler.py server/mergin/tests/test_project_handler.py
git show bfa644f8 -- web-app/packages/app/src/App.vue web-app/packages/admin-app/src/App.vue doc/editor-permission-map.md
```

Backend:

```bash
cd server
python -m pytest mergin/tests/test_project_handler.py -q
```

Frontend:

```bash
cd web-app
yarn lint:no-legacy
```

Si no hay entorno local completo, al menos verificar sintaxis Python:

```bash
python -m py_compile server/mergin/sync/project_handler.py server/mergin/tests/test_project_handler.py
```

## Resultado esperado

- Un usuario `editor` debe poder sincronizar cambios de features vía diff.
- Un usuario `editor` no debe poder subir cambios estructurales.
- Un usuario `writer` debe conservar comportamiento previo para cambios estructurales.
- La opción Editor debe aparecer en los dropdowns de permisos.

## Riesgo principal

El riesgo NO es que Editor no aparezca. El riesgo real es autorización:

> Si `get_push_permission(changes)` clasifica mal un cambio estructural como `Edit`, un Editor podría modificar el proyecto como si fuera Writer.

