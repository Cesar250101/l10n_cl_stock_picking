# Manual de Usuario — Guías de Despacho Electrónica para Chile

Módulo: `l10n_cl_stock_picking` · Odoo 16 · Localización chilena (SII)

Este manual explica, desde la perspectiva de quien usa el sistema (bodega, despacho, contabilidad), cómo configurar y operar la emisión de **Guías de Despacho Electrónicas** (DTE código 52) sobre las entregas (`stock.picking`) de Odoo.

> Este módulo depende de `l10n_cl_fe` (Facturación Electrónica Chilena) y reutiliza su certificado digital, sus folios CAF y su cola de envío al SII. Si todavía no tiene configurado el certificado digital ni sucursales SII, revise primero el manual de `l10n_cl_fe` (`MANUAL_USUARIO.md`, secciones 3.1 a 3.5) antes de continuar con este documento.

---

## 1. ¿Qué hace este módulo?

Permite que una entrega de bodega (`stock.picking`) se emita como Guía de Despacho Electrónica ante el SII, con el mismo circuito de timbrado y envío que usan las facturas:

- **Asignación de folio**: se asigna automáticamente al validar la entrega (no al crearla).
- **Timbrado electrónico**: firma el documento con el certificado digital de la compañía y genera el código de barras PDF417 que va impreso en la guía.
- **Envío al SII**: inmediato, diferido (en cola) o manual, según la configuración general de envío de DTE.
- **Envío masivo**: asistente para reenviar varias guías al SII de una sola vez.
- **Libro de Guías**: informe mensual/especial que agrupa todas las guías validadas y las envía al SII como libro electrónico.
- **Códigos adicionales por línea**: permite declarar códigos de barra u otros identificadores por cada producto despachado.
- **Aviso de guías pendientes de facturar**: alerta directamente en el formulario de la factura de venta.

### Requisitos previos

- Módulos: `stock`, `fleet`, `delivery`, `sale_stock`, `l10n_cl_fe` (se instalan automáticamente como dependencias).
- Certificado digital y folios CAF de tipo **Guía de Despacho Electrónica** cargados (ver manual de `l10n_cl_fe`).
- Cada **Bodega** (`stock.warehouse`) que vaya a emitir guías debe tener configurada su Sucursal SII, su tipo de documento y su secuencia de folios (ver sección 2 de este manual).

---

## 2. Configuración inicial

### 2.1 Configurar la Bodega para emitir Guías

**Inventario → Configuración → Almacenes**, abrir la bodega correspondiente. En la sección **"Configuraciones DTE"** que este módulo agrega al formulario:

| Campo | Qué es |
|---|---|
| **Modo Restauración** | Si está activo, la bodega deja de asignar folios al validar entregas — úselo solo al restaurar una copia de la base de datos, para no consumir folios reales por error. |
| **Sucursal SII** | Sucursal de la compañía asociada a esta bodega (ver manual de `l10n_cl_fe`, sección 3.5). |
| **Código de Sucursal SII** | Se completa solo a partir de la Sucursal SII elegida; no se edita directamente. |
| **Document Type** | Tipo de documento SII que emite esta bodega — debe ser el correspondiente a Guía de Despacho. |
| **Entry Sequence** | La secuencia de folios (CAF) que numerará las guías de esta bodega. Cárguela igual que un CAF de facturación (ver manual de `l10n_cl_fe`, sección 3.3/3.4), pero eligiendo el tipo de documento Guía de Despacho. |
| **Giros de la Bodega** | Giros económicos de la compañía que aplican a esta bodega (máximo 4). |

> **Importante:** el folio y el CAF viven en la **Bodega**, no en el Tipo de Operación (`stock.picking.type`). Todos los tipos de operación de una misma bodega (salidas, transferencias internas) comparten la misma secuencia de folios de Guía.

### 2.2 Qué tipos de entrega emiten Guía

Solo las entregas de **Salida** (`outgoing`) y **Transferencia Interna** (`internal`) piden folio y se timbran. Las **Recepciones** (`incoming`) nunca emiten Guía — el campo "Emitir Documento Tributario" no está disponible para ese tipo de operación.

---

## 3. Emitir una Guía de Despacho

### 3.1 Datos a completar antes de validar la entrega

Abra la entrega (**Inventario → Operaciones → Transferencias**, o desde una orden de venta). En el encabezado del formulario:

| Campo | Qué es |
|---|---|
| **Emitir Documento Tributario** (`use_documents`) | Se marca automáticamente al elegir un tipo de operación de Salida o Transferencia Interna. Desmárquelo si esta entrega no debe generar Guía electrónica. |
| **Tipo de documento** (`document_class_id`) | Se completa solo desde la configuración de la Bodega; requerido si "Emitir Documento Tributario" está activo. |
| **Folio** (`sii_document_number`) | Se muestra vacío/"Next Number" antes de validar — el folio real se asigna recién al validar la entrega (botón "Validar"). |

Junto al contacto del destinatario:

| Campo | Qué es |
|---|---|
| **Giro** (`activity_description`) | Giro comercial del cliente/receptor; se autocompleta desde su ficha de contacto. |
| **Moneda** | Moneda del documento (solo visible con multi-moneda activo). |
| **Contacto** (`contact_id`) | Persona de contacto específica del receptor, si es distinta al cliente principal. |

Datos del transporte (obligatorios si "Emitir Documento Tributario" está activo):

| Campo | Qué es |
|---|---|
| **Nombre Chofer** / **Rut Chofer** / **Patente** | Identificación de quien transporta la mercadería y del vehículo. |
| **Tipo de Despacho** | Despacho por cuenta de la empresa, por cuenta del cliente, despacho externo, o sin definir. Si elige "Despacho Externo", debe además indicar el **Transportista** (`carrier_id`). |
| **Razón del traslado** | Motivo SII del traslado: venta, ventas por efectuar, consignación, entrega gratuita, traslado interno, devolución, exportación, etc. Determina cómo el SII interpreta el documento — elíjalo con cuidado, ya que **"Traslados Internos"** no calcula impuestos. |

### 3.2 Líneas de detalle y montos

En la pestaña de líneas de producto, este módulo agrega:

- **Precio Unitario**, **Impuestos**, **Descuento** y **Subtotal** por línea — se completan automáticamente cuando la entrega proviene de una orden de venta o de compra (heredan precio/impuestos/descuento de la línea de venta), pero pueden editarse manualmente si la entrega es independiente.
- Los totales (**Neto**, **IVA**, **Total**) se recalculan automáticamente al pie del documento a partir de estas líneas.

> El sistema no permite mezclar en una misma guía líneas con impuesto "precio incluido" y líneas con impuesto "precio sin incluir" — si lo intenta, verá el error *"No se puede hacer timbrado mixto..."*. Revise que todas las líneas usen el mismo criterio de impuestos antes de validar.

### 3.3 Códigos Adicionales por línea (opcional)

Si necesita declarar un código adicional (por ejemplo, un código de barras específico del SII) para cada producto despachado:

1. Active el interruptor **"Definir Códigos Adicionales por Línea"** sobre la lista de productos. Si todavía no ha agregado ningún producto, el sistema le pedirá que agregue líneas primero.
2. Se habilita la pestaña **"Códigos Adicionales"**, con una fila por línea de producto.
3. Complete **Tipo Código** y **Valor Código** para cada línea que lo requiera.

### 3.4 Referencias a otros documentos (opcional)

En la pestaña **"Referencias DTE"** puede vincular esta guía con otro documento (por ejemplo, la orden de venta o un documento anterior que esta guía reemplaza o complementa), indicando el **Folio** de origen, el **Tipo de Documento** referenciado y la fecha.

### 3.5 Validar la entrega y emitir la Guía

1. Presione **Validar** en la entrega, como en cualquier transferencia de Odoo.
2. Si "Emitir Documento Tributario" está activo, el sistema en ese momento:
   - Asigna el siguiente folio disponible de la secuencia de la Bodega.
   - Timbra el documento (genera el XML DTE y el código de barras).
   - Según el **método de envío configurado** (Ajustes → Facturación Electrónica → "Método de envío DTE": inmediato/diferido/manual), envía la guía al SII de inmediato, la deja en cola para envío diferido, o la deja pendiente de envío manual.
3. Aparece una nueva pestaña **"Facturación Electrónica"** en el formulario de la entrega, con:
   - El **estado del envío** (`sii_result`) en la barra de estado: No Enviado → En cola de envío → Enviado → En Proceso → Aceptado/Rechazado/Reparo.
   - El **código de barras PDF417** ya generado.
   - El **mensaje de respuesta del SII**, una vez que llega.
   - El **XML del DTE**, para revisión técnica si es necesario.

### 3.6 Botones de la pestaña "Facturación Electrónica"

| Botón | Cuándo aparece | Qué hace |
|---|---|---|
| **Send XML** | Entrega validada, estado "No Enviado" | Envía la guía al SII de inmediato (uso manual, si el método de envío configurado es "manual"). |
| **ReSend XML** | Entrega validada, estado "Rechazado" | Reintenta el envío después de corregir el motivo del rechazo. |
| **Ask for DTE** | Entrega validada, ya enviada | Consulta al SII el estado actual de aceptación/rechazo y actualiza el resultado. |
| **Download XML** | Entrega validada, ya enviada | Descarga el archivo XML del DTE de la guía. |

---

## 4. Envío masivo de Guías al SII

Si tiene varias guías pendientes de enviar (por ejemplo, después de un problema de conexión), puede reenviarlas todas juntas:

1. Vaya a la lista de **Transferencias** (**Inventario → Operaciones → Transferencias**), en vista de lista.
2. Seleccione las guías a reenviar (checkbox a la izquierda de cada fila).
3. Abra el menú de acciones (⚙️) y elija **"Enviar Guías de despacho al SII"**.
4. En el asistente, revise la lista de documentos (folio, origen, total), complete opcionalmente el **Número de atención** y confirme con **"Confirm"**.
5. El sistema encola/envía todas las guías seleccionadas de una vez.

> El checkbox **"Es set de pruebas"** aparece marcado por defecto cuando la compañía está en ambiente de certificación (SIICERT); no lo desmarque a menos que su empresa ya esté operando en producción real ante el SII.

---

## 5. Libro de Guías (informe mensual)

El **Libro de Guías** agrupa todas las guías validadas de un período y las declara al SII como libro electrónico, igual que el Libro de Compra/Venta de facturación.

Acceso: **Contabilidad → Informes → Libros Cierre de Mes** (o el menú equivalente configurado por su administrador).

1. Cree un registro nuevo. Complete:
   - **Detalle**: nombre descriptivo del libro.
   - **Periodo Tributario**: mes que declara, formato `AAAA-MM` (se sugiere el mes actual por defecto).
   - **Tipo de Libro**: actualmente solo existe la opción **"Especial"**.
   - **Tipo de Envío**: Total, Parcial o Ajuste, según corresponda a lo que está declarando.
   - **Folio de Notificación**: obligatorio solo si el Tipo de Libro es "Especial".
2. En la pestaña **"Movimientos"**, agregue las guías (`stock.picking`) que componen este libro.
3. Presione **"Validate"** para pasar el libro a estado listo para envío.
4. Presione **"Send XML"** para enviarlo al SII. El estado avanza por la misma secuencia que un DTE individual: No Enviado → En Cola → Enviado → En Proceso → Aceptado/Rechazado/Proceso.
5. Use **"Ask for DTE"** para consultar el resultado, y **"Download XML"** para descargar el XML enviado.

---

## 6. Relación entre Guías y Facturas

Una Guía de Despacho es un documento independiente — no genera automáticamente una factura, ni una factura genera automáticamente una guía. Se vinculan solamente por referencia:

- Al emitir una **factura de venta** que referencia el folio de una guía (pestaña "Otra Información" de la factura, sección de referencias), el sistema marca esa guía como **Facturada** (campo "Invoiced?").
- Si un cliente tiene guías **aceptadas o con reparo que todavía no han sido facturadas** dentro del período de facturación vigente (el mes en curso, o el mes anterior si está facturando entre el día 1 y el 10), el formulario de la factura muestra:
  - Un aviso azul: *"Tiene guías de despacho no facturadas para este cliente..."*
  - Un botón de estadística **"Guías de Despachos Pendientes"** en la esquina superior del formulario, que al presionarlo abre la lista de esas guías para que pueda revisarlas y referenciarlas.

---

## 7. Preguntas frecuentes / solución de problemas

**Al validar la entrega no se generó folio ni se timbró la guía.**
Revise que "Emitir Documento Tributario" esté marcado y que el tipo de operación sea Salida o Transferencia Interna (las Recepciones nunca timbran). Verifique también que la Bodega tenga configurados Tipo de documento y Secuencia de folios (sección 2.1).

**Error "No se puede hacer timbrado mixto...".**
Alguna línea de producto tiene un impuesto "precio incluido" y otra tiene un impuesto "precio sin incluir" dentro de la misma guía. Revise los impuestos asignados a cada línea y unifique el criterio antes de validar.

**El folio salió repetido o distinto al que esperaba.**
El sistema hace una verificación de seguridad al validar: si el siguiente número de la secuencia ya está en uso por otra guía de la misma bodega, salta automáticamente al primer folio realmente disponible. Esto es una protección contra el desfase de la secuencia, no un error — no edite el folio manualmente para "corregirlo".

**El interruptor de Códigos Adicionales no deja ver las líneas recién agregadas.**
Guarde la entrega (o valide) después de agregar los productos; las líneas nuevas de una guía sin guardar a veces no se pueden enlazar en pantalla hasta que existen en la base de datos — el sistema las reconstruye automáticamente al guardar.

**Quiero desinstalar el módulo y Odoo no me deja.**
Si existe al menos una Guía con envío **Aceptado** por el SII, el sistema bloquea la desinstalación para no perder el historial de un documento tributario ya validado ante el SII. No hay una ruta de migración automática para sacar esos documentos del módulo.

**El aviso de "guías pendientes de facturar" no aparece en la factura.**
Solo se muestra en facturas de venta (`out_invoice`) y solo considera guías con resultado **Proceso** o **Reparo** que aún no estén marcadas como facturadas, dentro de la ventana de fechas del período de facturación vigente. Confirme que la guía cumpla esas tres condiciones.

---

## 8. Limitaciones conocidas

- El folio y el CAF de las guías se configuran por **Bodega**, no por Tipo de Operación: si una bodega despacha desde varios tipos de operación, todos comparten la misma numeración.
- El "Libro de Guías" solo ofrece el Tipo de Libro **"Especial"** — no hay opción de libro mensual regular distinta.
- No existe una ruta de migración de datos para desinstalar el módulo si ya tiene guías Aceptadas por el SII; el sistema bloquea la desinstalación en ese caso.
