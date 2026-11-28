# Guía para voluntarios — el sitio web de Grapevine / La Viña

*Dos páginas para los voluntarios del comité. No hace falta saber programar. In English:
[VOLUNTEER-GUIDE.md](VOLUNTEER-GUIDE.md).*

El sitio web ([grapevine.neta65.org](https://grapevine.neta65.org/), en español
[/es/](https://grapevine.neta65.org/es/)) **se actualiza solo unas cuatro veces al día**: un robot en GitHub lee la
carpeta de Google Drive del comité, los sitios de las revistas, los pódcasts y YouTube, traduce lo nuevo y publica
el sitio. Nadie tiene que oprimir nada. Si una actualización falla, el sitio sigue mostrando la última versión
buena hasta que la siguiente funcione.

## 1. ¿Funciona el sitio?

Revise en este orden (cada paso toma unos segundos):

1. **La página de Estado** — [grapevine.neta65.org/es/status/](https://grapevine.neta65.org/es/status/). **Al día**
   en verde junto a cada fuente quiere decir que todo está bien (una fuente con un problema lo dice en rojo). También
   muestra a qué hora llegó la cita del día cada mañana. Entre los calendarios opcionales, el de talleres de NETA 65
   aparece **En pausa**: su sitio bloquea a los robots, así que esos eventos se agregan a mano. Es a propósito; no
   hay nada que hacer.
2. **La insignia** al principio del [README](../README.md) del repositorio: verde = la última actualización
   funcionó.
3. **La pestaña Actions** — [github.com/NETA65/aagrapevine/actions](https://github.com/NETA65/aagrapevine/actions).
   Cada ejecución tiene un ✓ (funcionó) o una ✗ (falló). Las que importan:
   - **Website update** — la actualización misma (cuatro veces al día, y después de cada cambio que se guarda);
   - **Morning check (new day by 5:30 AM)** — pone el nuevo día y la cita del día en el sitio por la mañana;
   - **Code check** — prueba un cambio al código; una ✗ roja aquí nunca deja el sitio caído.
4. **La pestaña Issues** — [github.com/NETA65/aagrapevine/issues](https://github.com/NETA65/aagrapevine/issues).
   El robot abre un *issue* (aviso) por sí solo cuando algo necesita a una persona, y lo cierra solo cuando se
   arregla.

## 2. Algo está en rojo: ¿qué hago?

- **Una sola ✗ roja:** casi siempre, nada. Espere la siguiente ejecución (unas horas). El sitio no se ve afectado.
- **Un aviso (issue) abierto por el robot:** ábralo y siga la parte **What to do** ("Qué hacer"). Los más comunes:
  - *"The website update keeps failing"* — dos actualizaciones fallidas seguidas. Abra la ejecución enlazada, haga
    clic en el trabajo con la ✗ roja y lea el paso en rojo. Si lo causó el último cambio de alguien, deshaga ese
    cambio.
  - *"A content source has stopped updating"* — una fuente (Drive, Instagram, un pódcast…) lleva una semana sin
    funcionar. El aviso dice qué revisar para esa fuente.
  - *"Broken links found by the weekly check"* — un enlace del sitio ya no funciona; el aviso los enumera.
  - *"The daily quote missed the morning goal"* — solo cuando la alarma de la mañana esté configurada (sección 4).
- **La cita del día no aparece por la mañana:** Actions → **Morning check (new day by 5:30 AM)** → **Run workflow**
  → **Run workflow**. Solo hace lo que falta, y se puede oprimir en cualquier momento.
- **Nunca hace falta:** borrar ejecuciones, editar archivos de `data/` ni cambiar ajustes que no entienda. Si tiene
  dudas, pregunte (sección 5): mientras tanto, el sitio sigue funcionando.

## 3. ¿Cómo agrego algo?

| Quiero agregar… | Dónde | Guía paso a paso (en inglés) |
|---|---|---|
| Un volante o un evento | En Drive: **A65_GV › 2027-2028_Panel77_GVLV › flyers** (nombre de archivo que empieza con la fecha), o un archivo en `content/events/` | [Flyers and events](../how-to/flyers-and-events.md) · [content/events/README.md](../content/events/README.md) |
| Una publicación del boletín | En Drive: **A65_GV › 2027-2028_Panel77_GVLV › bulletin**, o un archivo en `content/bulletin/` | [Bulletin](../how-to/bulletin.md) |
| Fotos, presentaciones, un informe | En Drive: las carpetas `photos`, `slides` y `reports` de **A65_GV › 2027-2028_Panel77_GVLV** | [Photos, slides and reports](../how-to/photos-slides-reports.md) |
| Algo para la pantalla de la mesa (booth) | En Drive: **A65_GV › 2027-2028_Panel77_GVLV › booth** | [The booth display](../how-to/booth.md) |
| Un cambio de ajuste (hora de la reunión, un enlace) | `config/site.yml` | [Settings](../how-to/settings.md) |
| Una mejor traducción al español | `data/translations/overrides.yml` | [Translations](../how-to/translations.md) |

El sitio lee solo las carpetas que están dentro de una carpeta de Panel (hoy **2027-2028_Panel77_GVLV**, en la
carpeta compartida **A65_GV**): [The Drive panel folder](../how-to/drive-panel-folder.md) (en inglés) las enumera
todas.

Todas las guías: [how-to/README.md](../how-to/README.md) ("I want to… → read this"). Un archivo de Drive aparece en
el sitio después de la siguiente actualización (unas horas como máximo); un archivo guardado en el repositorio
inicia una actualización en pocos minutos.

## 4. La alarma de la mañana (para configurar más adelante)

Mientras no esté configurada, el propio horario de GitHub pone el nuevo día y la cita del día en el sitio: a veces
se atrasa, así que algunas mañanas la cita puede llegar después de las 5:30 a. m. La **alarma de cron-job.org**
asegura la mañana: un despertador externo y gratuito oprime "Run workflow" a las 4:30 a. m. (hora del Centro).
Configurarla toma unos 10 minutos y se renueva una vez al año (la clave vence):
[OPERATIONS → Set up the cron-job.org alarm later](OPERATIONS.md#set-up-the-cron-joborg-alarm-later). En resumen:
un **token de acceso detallado** (*fine-grained token*) de GitHub solo para este repositorio, con **Actions: Read
and write**; va en el encabezado **Authorization** de la tarea de cron-job.org (nunca en el repositorio); la tarea
llama a `POST https://api.github.com/repos/NETA65/aagrapevine/actions/workflows/morning.yml/dispatches` con el
cuerpo `{"ref":"main"}`. Después, ponga `morning_alarm: true` en `config/site.yml`.

## 5. A quién preguntar

- **El contacto del comité para el sitio web:** [grapevine@neta65.org](mailto:grapevine@neta65.org) — la persona
  que preside el comité o quien cuida el sitio (tienen la cuenta de GitHub **NETA65** y la carpeta de Google Drive).
- **Un problema con neta65.org** (el sitio del Área, su calendario): el administrador del sitio web del Área, por
  medio de [neta65.org](https://neta65.org).
- **Para quien cuida el código:** el [README](../README.md), [docs/OPERATIONS.md](OPERATIONS.md) y
  [Automation and troubleshooting](../how-to/automation-and-troubleshooting.md) tienen todos los detalles.
