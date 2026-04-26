---
title: "Credit Card"
knowledge_domain: bian
source_type: "markdown_curated"
document_name: "bian-web-credit-card"
version: "1.0"
language: "es"
summary: "Service Domain BIAN que orquesta el ciclo de vida operativo y transaccional de una tarjeta de crédito."
tags:
  - bian
  - service-domain
  - arquitectura
source_url: ""
author: "OpenAI"
last_reviewed: "2026-04-15"
status: draft
---

# Descripción general

Credit Card es el dominio BIAN responsable de orquestar la operación integral del producto tarjeta de crédito. Cubre la administración de la cuenta de tarjeta, el procesamiento de transacciones, la facturación, el cobro de pagos, la aplicación de intereses y comisiones, y la gestión de dispositivos emitidos asociados a la cuenta.

# Propósito de negocio

Proveer una capacidad unificada para operar el producto de tarjeta de crédito durante todo su ciclo de vida, desde el alta de la cuenta hasta la operación recurrente del plástico o dispositivo digital, incluyendo obligaciones financieras y eventos operativos propios del producto.

# Capacidades principales

- Alta y mantenimiento de la cuenta de tarjeta de crédito.
- Ejecución de billing, repayment y aplicación de fees/intereses.
- Gestión de transacciones de cuenta de tarjeta y de dispositivos emitidos.
- Administración de planes de crédito vinculados a la cuenta.
- Control operativo de la cuenta, incluyendo suspensión y recuperación de información.

# Relación con otros dominios

Se relaciona estrechamente con Card Authorization para la aprobación en línea, con Card Transaction Capture para el registro de operaciones, con Card Clearing y Card Financial Settlement para post-autorización y liquidación, y con dominios de cliente, casos y servicing para atención operativa.

# Aplicabilidad en arquitectura

Aplica cuando la solución necesita modelar el producto de tarjeta de crédito como capacidad de negocio central. Es especialmente útil para diseños de issuer processing, back-office de tarjetas, servicing del producto, billing engine y experiencias omnicanal donde la tarjeta es un objeto financiero principal.

# Observaciones

No debe confundirse con los dominios especializados del flujo transaccional. Credit Card gobierna el producto y su operación integral; la autorización, captura, clearing y settlement se apoyan en dominios especializados distintos. Conviene usarlo como dominio “anchor” del producto y no sobrecargarlo con lógica de switch o integración de red.

# Referencias

- BIAN Service Landscape V13.0 Value Chain View
- BIAN Credit Card Service Domain