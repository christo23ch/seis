import type { Usuario } from "./types";

/** Roles con capacidad de escritura. Espejo de `ROLES_ESCRITURA` en
 * `backend/app/api/deps.py` («admin», «analista»): si cambia allí, cambia aquí. */
const ROLES_ESCRITURA: readonly string[] = ["admin", "analista"];

/** ¿Mostrar los controles de escritura (crear, validar, emitir…)?
 *
 * SOLO decide qué botones se ven. La autorización real la hace el backend en
 * cada petición: un «lector» que llamara a la API directamente recibiría 403
 * igualmente, oculte esto lo que oculte. */
export function puedeEscribir(usuario: Usuario | null | undefined): boolean {
  return !!usuario && ROLES_ESCRITURA.includes(usuario.rol);
}
