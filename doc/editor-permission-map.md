# Mapa para activar el rol Editor en Community Edition

Este documento mapea el estado actual del rol `editor` en `server_merg` y las reglas que habría que respetar antes de tocar código. La conclusión corta: **Editor ya existe parcialmente, pero no está operativo de forma segura en CE**.

## Respuesta rápida

No hay que inventar el rol desde cero.

Actualmente el proyecto ya tiene:

- modelo backend para `ProjectRole.EDITOR`;
- migraciones que contemplan `editor/editors`;
- tipos, labels y dropdown options en frontend;
- APIs que aceptan el string `editor`.

Pero todavía falta lo crítico:

1. **Mostrarlo en UI**: hoy está filtrado explícitamente.
2. **Permitir push limitado**: hoy CE exige permiso `Upload`, equivalente práctico a `writer`, para crear versiones.
3. **Validar reglas Editor**: permitir edición de features, pero bloquear cambios estructurales.

## Reglas funcionales que debe cumplir Editor

Según la documentación oficial de Mergin Maps y la release donde se introdujo Editor, el rol debe permitir trabajo de campo, no administración del proyecto.

| Acción | Editor |
|---|---|
| Ver proyecto, datos e historial | Sí |
| Descargar/sincronizar datos del proyecto | Sí |
| Agregar, editar o borrar features/filas | Sí |
| Agregar fotos/adjuntos asociados a features | Sí |
| Agregar archivos comunes no estructurales | Sí, con restricciones |
| Agregar, modificar o borrar `.qgs` / `.qgz` | No |
| Agregar, modificar o borrar `mergin-config.json` | No |
| Borrar archivos `.gpkg` | No |
| Cambiar schema de GeoPackage | No |
| Agregar/quitar capas o campos del proyecto | No |
| Cambiar propiedades de capas o proyecto QGIS | No |
| Compartir, borrar o transferir proyecto | No |

**Punto clave:** Editor no protege contra descarga de datos. Protege contra cambios estructurales.

## Mapa de archivos actuales

### Backend: modelo y roles

| Archivo | Estado actual | Qué significa |
|---|---|---|
| `server/mergin/sync/models.py` | `ProjectRole` define `READER`, `EDITOR`, `WRITER`, `OWNER`. | El rol existe en el dominio. No hay que crearlo. |
| `server/mergin/sync/models.py` | `ProjectRole.__ge__` compara roles por orden. | `editor` está entre `reader` y `writer`. No cambiar el orden. |
| `server/mergin/sync/models.py` | `members_by_role(ProjectRole.EDITOR)` incluye editores y superiores. | La serialización por niveles ya puede incluir `editors`. |
| `server/mergin/sync/models.py` | `bulk_roles_update()` itera roles incluyendo `EDITOR`. | La actualización masiva de permisos ya soporta editor. |

### Backend: permisos

| Archivo | Estado actual | Qué significa |
|---|---|---|
| `server/mergin/sync/permissions.py` | `ProjectPermissions.Edit` permite `ProjectRole.EDITOR` o superior. | La capa de autorización ya entiende “puede editar”. |
| `server/mergin/sync/permissions.py` | `ProjectPermissions.Upload` exige `ProjectRole.WRITER` o superior. | Este es el bloqueo real para Editor en pushes completos. |
| `server/mergin/sync/permissions.py` | `get_user_project_role()` devuelve `EDITOR` si pasa `Edit`. | La API puede reportar el rol efectivo como editor. |

### Backend: push/sync

| Archivo | Estado actual | Qué significa |
|---|---|---|
| `server/mergin/sync/project_handler.py` | `get_push_permission(changes)` devuelve siempre `ProjectPermissions.Upload`. | En CE, todo push requiere Writer. Acá está la pieza central a cambiar. |
| `server/mergin/sync/public_api_controller.py` | Push v1 usa `get_push_permission(changes)`. | Si se cambia la regla, impacta sync v1. |
| `server/mergin/sync/public_api_v2_controller.py` | Crear versión v2 usa `get_push_permission(changes)`. | Si se cambia la regla, impacta sync v2. |
| `server/mergin/sync/public_api_v2_controller.py` | `upload_chunk()` usa `ProjectPermissions.Edit`. | Editor puede pasar la carga de chunks, pero no necesariamente finalizar versión. |

### Backend: APIs de colaboradores

| Archivo | Estado actual | Qué significa |
|---|---|---|
| `server/mergin/sync/public_api_v2_controller.py` | `add_project_collaborator()` usa `ProjectRole(request.json["role"])`. | Acepta `editor` si llega desde frontend/API. |
| `server/mergin/sync/public_api_v2_controller.py` | `update_project_collaborator()` usa `ProjectRole(request.json["role"])`. | Puede actualizar un colaborador a `editor`. |
| `server/mergin/sync/public_api_controller.py` | `parse_project_access_update_request()` incluye `editors` y `editorsnames`. | La API legacy también reconoce editor. |
| `server/mergin/sync/schemas.py` | `ProjectAccessSchema` serializa `editors`. | Las respuestas pueden devolver editores. |

### Base de datos / migraciones

| Archivo | Estado actual | Qué significa |
|---|---|---|
| `server/migrations/community/54c2c49fe2c7_add_editors.py` | Agrega columna `editors` a `project_access`. | CE ya tuvo migración para editores en esquema legacy. |
| `server/migrations/community/d02961c7416c_add_project_member_table.py` | Enum `project_role` incluye `editor`. | El esquema nuevo `project_user` ya soporta editor. |

**Conclusión DB:** salvo una instalación vieja sin migrar, no debería hacer falta una migración nueva sólo para el rol `editor`.

### Frontend: permisos y dropdowns

| Archivo | Estado actual | Qué significa |
|---|---|---|
| `web-app/packages/lib/src/common/permission_utils.ts` | `ProjectRole` incluye `editor`. | El tipo existe. |
| `web-app/packages/lib/src/common/permission_utils.ts` | `getProjectRoleNameValues()` incluye label `Editor`. | La opción existe para dropdowns. |
| `web-app/packages/lib/src/common/permission_utils.ts` | `getProjectPermissionsValues()` incluye permiso `edit`. | La UI entiende permiso “edit”. |
| `web-app/packages/lib/src/common/permission_utils.ts` | `editor` mapea a `editorsnames` y `edit`. | El payload hacia backend ya tiene mapping. |
| `web-app/packages/lib/src/modules/project/store.ts` | `availableRoles` se inicializa con todos los roles. | El store arranca con Editor disponible. |
| `web-app/packages/lib/src/modules/project/store.ts` | `filterPermissions()` remueve roles/permisos. | Es el mecanismo usado para ocultar Editor. |
| `web-app/packages/app/src/App.vue` | Llama `projectStore.filterPermissions(['editor'], ['edit'])`. | Oculta Editor en dashboard normal. |
| `web-app/packages/admin-app/src/App.vue` | Llama `projectStore.filterPermissions(['editor'], ['edit'])`. | Oculta Editor en admin app. |
| `web-app/packages/lib/src/modules/project/components/ProjectMembersTable.vue` | Usa `projectStore.availableRoles` para seleccionar roles. | Al dejar de filtrar, Editor aparecería en gestión de miembros. |
| `web-app/packages/lib/src/modules/project/components/ProjectShareDialog.vue` | Envía `editorsnames` si se elige Editor. | Compartir con Editor ya está cableado. |

## Cambio mínimo vs cambio correcto

### Cambio mínimo visual

Quitar el filtro de `editor` en:

- `web-app/packages/app/src/App.vue`
- `web-app/packages/admin-app/src/App.vue`

**Resultado:** Editor aparece en la UI.

**Riesgo:** alto. Si el backend no permite pushes de Editor, la UI promete algo que no funciona. Si se relaja mal el backend, Editor podría terminar con poder de Writer.

### Cambio correcto

El cambio correcto debe partir de `server/mergin/sync/project_handler.py`.

La idea:

```text
get_push_permission(changes)
  si todos los cambios son compatibles con Editor:
    devolver ProjectPermissions.Edit
  si algún cambio es estructural:
    devolver ProjectPermissions.Upload
```

Después recién se desbloquea la UI.

## Reglas de clasificación para `get_push_permission(changes)`

`changes` llega con listas similares a:

- `added`
- `updated`
- `removed`

Cada item contiene al menos `path` y datos de archivo/diff.

### Debe requerir Writer (`ProjectPermissions.Upload`)

| Condición | Motivo |
|---|---|
| Path termina en `.qgs` o `.qgz` | Cambia el proyecto QGIS. |
| Path es `mergin-config.json` | Cambia configuración de sincronización/proyecto. |
| Se elimina un `.gpkg` | Elimina una capa/dataset. |
| Se agrega un `.gpkg` como nueva capa/dataset | Agrega estructura de datos. |
| Se actualiza `.gpkg` sin diff basado en GeoDiff | Puede representar cambio binario o estructural no verificable. |
| El diff de `.gpkg` contiene cambios de schema | Agrega/quita campos/tablas/estructura. |
| Se eliminan conflict files | La release oficial indica que Editor no debe editar/borrar conflict files. |

### Puede requerir sólo Editor (`ProjectPermissions.Edit`)

| Condición | Motivo |
|---|---|
| Update de `.gpkg` con diff válido y sin cambio de schema | Edición de features/filas. |
| Agregar/actualizar adjuntos no estructurales | Fotos/archivos de campo. |
| Remover adjuntos no estructurales | Limpieza de archivos relacionados a features. |

## Tests necesarios antes de confiar en esto

No alcanza con probar “aparece en el dropdown”. Hay que probar autorización.

| Área | Archivo sugerido | Caso |
|---|---|---|
| Clasificación de cambios | `server/mergin/tests/test_project_handler.py` | `get_push_permission()` devuelve `Edit` para diff de GeoPackage sin schema change. |
| Clasificación de cambios | `server/mergin/tests/test_project_handler.py` | Devuelve `Upload` para `.qgs`, `.qgz`, `mergin-config.json`. |
| Clasificación de cambios | `server/mergin/tests/test_project_handler.py` | Devuelve `Upload` al borrar `.gpkg`. |
| Permisos push | `server/mergin/tests/test_permissions.py` o API tests | Usuario Editor puede pasar push permitido. |
| Permisos push | API tests v1/v2 | Usuario Editor recibe 403 en cambios estructurales. |
| UI | tests frontend existentes o verificación manual | Editor aparece en dropdowns luego del cambio. |

## Orden recomendado de implementación

1. Agregar tests de backend para la clasificación de `changes`.
2. Implementar la lógica en `server/mergin/sync/project_handler.py`.
3. Probar que Editor puede hacer sólo cambios permitidos.
4. Recién después quitar el filtro del frontend.
5. Probar flujo real desde dashboard + cliente/QGIS/mobile si está disponible.

## Riesgos

| Riesgo | Por qué importa |
|---|---|
| Falso Editor | Si sólo se muestra la UI, el usuario queda con un rol que no puede sincronizar correctamente. |
| Editor demasiado permisivo | Si se permite todo push con `Edit`, Editor se vuelve Writer disfrazado. |
| Cambios GeoPackage mal detectados | El schema puede cambiar dentro de `.gpkg`; hay que distinguir datos vs estructura. |
| Compatibilidad cliente | QGIS plugin/mobile pueden depender del campo `permissions.upload`. Actualmente ese campo usa `ProjectPermissions.Edit`, pero el push final depende de `get_push_permission()`. |

## Referencias externas

- Mergin Maps permissions: https://merginmaps.com/docs/manage/permissions/
- Release 2024.4.0 con reglas de Editor: https://github.com/lutraconsulting/mergin/releases

