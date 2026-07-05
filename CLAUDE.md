# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this module does

`l10n_cl_stock_picking` (Odoo 16) extends `stock.picking` so that deliveries can be issued as a Chilean SII electronic Guía de Despacho (DTE code 52): folio assignment, signing/"timbrado", sending to the SII (sync or queued), a monthly "Libro de Guías" report, and a bulk-send wizard. It mirrors the same architectural patterns used by `l10n_cl_fe` (base electronic invoicing) and `l10n_cl_dte_point_of_sale` (POS boletas) — read those modules' `CLAUDE.md` first if unfamiliar with the shared conventions (`sii.document_class`, `dte.caf`, `sii.xml.envio`, `sii.cola_envio`, digital signature via `get_digital_signature`).

Depends on: `stock`, `fleet`, `delivery`, `sale_stock`, `l10n_cl_fe`. Runtime Python deps (not in `external_dependencies`, inherited from `l10n_cl_fe`): `facturacion_electronica`, `pdf417gen`, `PIL`.

This addon has its own git repository (`.git` inside this directory, remote `github.com/Cesar250101/l10n_cl_stock_picking`, branch `16.0`) — independent from the main Odoo checkout. Commit from inside this directory, not from the server root.

## Commands

No dedicated test suite, linter, or build step. Development/verification is done by running the Odoo server against this addon:

```bash
./odoo-bin -c <config> -u l10n_cl_stock_picking -d <database> --stop-after-init
```

## Architecture

### Folio assignment happens on `_action_done`, not on creation

Unlike sales documents, a Guía's SII folio is assigned when the picking is validated (`StockPicking._action_done()` in [models/stock_picking.py](models/stock_picking.py)), not when the record is created. It pulls the next number from `picking_type_id.warehouse_id.sequence_id`, then does a defensive raw-SQL `MAX(sii_document_number)` re-check against other `stock_picking` rows for the same `document_class_id`/company before committing to it (guards against sequence drift, mirroring the advisory-lock pattern in `l10n_cl_dte_point_of_sale`, though here it's a plain re-check rather than a Postgres advisory lock). Folio numbering, CAF, and sequence all live on **`stock.warehouse`** (`document_class_id`, `sequence_id`, `sucursal_id`), not on `stock.picking.type` — a warehouse has one Guía sequence shared by all its picking types.

Only `outgoing`/`internal` pickings actually timbra and enqueue for SII send; `incoming` pickings never get `use_documents=True` (see `set_use_document()`/`onchange_picking_type`). `restore_mode` on the warehouse skips folio assignment entirely (used for restoring a DB backup without re-consuming real folios).

### DTE generation/signing/sending pipeline

`stock.picking` builds the DTE dict piece by piece, mirroring `l10n_cl_fe`'s `account.move` and `l10n_cl_dte_point_of_sale`'s `pos.order`:
`_picking_lines()` (detail lines + `CdgItem` additional codes) → `_encabezado()` (= `_id_doc` + `_receptor` + `_transporte` + `_totales`) → `_dte()` (adds `Referencia` lines, e.g. linking back to the sale invoice) → `_timbrar()` (calls `fe.timbrar`, stores `sii_xml_dte`/`sii_barcode`) → `_crear_envio()`/`do_dte_send()` (calls `fe.timbrar_y_enviar`, creates/updates an `sii.xml.envio` record, model `stock.picking` via `picking_ids`).

- `do_dte_send_picking()` is the manual/bulk entry point (used by the masive-send wizard); `_action_done()` is the entry point during normal delivery validation, driven by the `account.send_dte_method` system parameter (`inmediato`/`diferido`/`manual`) exactly like the other DTE-emitting modules.
- `ask_for_dte_status()` / `_get_dte_status()` poll the SII for Aceptado/Rechazado and update `sii_result`.
- `dte_caf.py` extends `dte.caf`'s CAF-scan queries (`_get_tables`, `_join_inspeccionar`, `_where_inspeccionar`) to also look at `stock_picking` when the document class `es_guia()`.

### Additional item codes ("Códigos Adicionales") — client/server sync workaround

`use_codigos_adicionales` toggles a per-line `stock.move.cdg.item` (`TpoCodigo`/`VlrCodigo`, e.g. barcodes) that gets embedded as `CdgItem` in the DTE detail lines. Because the web client can't reliably link a `stock.move.cdg.item` to a `stock.move` that hasn't been saved yet on a brand-new picking, `create()`/`write()` on `stock.picking` run `_strip_unlinked_cdg_items()` (drops any `(0,0,...)` command missing `move_id`) followed by `_sync_codigos_adicionales()` (re-creates one `stock.move.cdg.item` per move once real IDs exist). Don't "fix" the onchange to force the link client-side — the server-side reconciliation is the intended mechanism.

### Guías vs. invoices: cross-references, not a shared document flow

A Guía is a standalone `stock.picking` with `document_class_id` domain-restricted to `sii.document_class` records where `document_type = 'stock_picking'`. It links to sales/invoices only via `stock.picking.referencias` (`origen` = folio, `sii_referencia_TpoDocRef`) and, in the other direction, `models/account_move.py` extends `account.move._post()` to flip `stock.picking.invoiced` when an invoice references a Guía's folio (`ref.sii_referencia_TpoDocRef.es_guia()`), and computes `has_pending_pickings`/`picking_pending_ids` on the invoice (done/Reparo Guías not yet invoiced for that customer, scoped to the current month or the prior month if invoicing on/after the 10th).

`ir_module_module.py` blocks uninstalling this module (`modules_to_remove`/`button_uninstall`) if any `sii.xml.envio` with state `Aceptado` still references a `stock.picking` — there is no data-migration path for accepted DTEs off this module.

### Libro de Guías (`stock.picking.book`)

Monthly/special report (model `models/libro.py`), analogous to `l10n_cl_fe`'s Libro de Compra/Venta: groups validated Guías by `document_class_id.sii_code`, calls `fe.libro(...)`, wraps the result in an `sii.xml.envio`, and drives the same `NoEnviado → EnCola → Enviado → ... → Proceso/Rechazado` state machine via `do_dte_send_book()`/`ask_for_dte_status()`.

### Pricing/tax fields propagate across the procurement chain

`precio_unitario`, `discount`, and `move_line_tax_ids` are added to `stock.move`, `procurement.group`, and carried through by `stock_rule.py` (`_get_custom_move_fields`, `_get_stock_move_values`) and `sale_order.py`/`purchase_order.py` (`_prepare_procurement_values`/`_prepare_stock_moves`) — this is how a sale order line's price/discount/taxes end up on the delivery's `stock.move` so the Guía can be timbrada with real amounts instead of zeros. When touching pricing on deliveries created from sales or purchases, check both ends of this chain, not just `stock_picking.py`.

### Conventions specific to this module

- Money/qty rounding goes through `self.currency_id.round(...)`, consistent with `l10n_cl_fe`.
- `move.quantity_done` is preferred over `product_uom_qty` wherever a quantity is needed for the DTE or tax computation (falls back to the ordered qty if `quantity_done` is 0) — a delivery isn't "real" for SII purposes until it has done quantities.
- SII tax codes are read off `account.tax.sii_code` (14/15/17 = IVA, 26/27/28/35/271 = additional/specific taxes needing `CodImpAdic`), matching the convention in `l10n_cl_fe`/`l10n_cl_dte_point_of_sale`.
