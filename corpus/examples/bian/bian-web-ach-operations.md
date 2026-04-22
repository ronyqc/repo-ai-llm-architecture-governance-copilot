---
title: "ACH Operations"
knowledge_domain: bian
source_type: "markdown_curated"
document_name: "bian-web-ach-operations"
version: "1.0"
language: "es"
summary: "Service Domain BIAN para la interfaz operativa con cámaras de compensación externas tipo ACH/CCE."
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

ACH Operations es el dominio BIAN que maneja la interfaz operativa con una cámara de compensación automatizada externa. Representa la capacidad necesaria para intercambiar lotes, controlar sesiones operativas y gestionar procesos de clearing, settlement y reconciliación con la red externa.

# Propósito de negocio

Permitir que el banco se conecte y opere de forma controlada con una infraestructura externa de compensación, como un ACH o una cámara de compensación equivalente, soportando tanto envíos como recepciones.

# Capacidades principales

- Gestión de la sesión operativa de acceso ACH.
- Manejo de lotes inbound y outbound.
- Warehousing de lotes salientes.
- Procesamiento de clearing y settlement de lotes ACH.
- Reconciliación de transacciones procesadas por la cámara.
- Parametrización del calendario y schedule operativo.

# Relación con otros dominios

Se relaciona con Payment Rail Operations, Payment Execution, Payment Order o Payment Instruction según la arquitectura del banco. También puede integrarse con dominios contables, reconciliación y contrapartes externas.

# Aplicabilidad en arquitectura

Muy relevante cuando la solución debe conectarse con una entidad externa como la CCE, una ACH nacional o una infraestructura batch de compensación interbancaria. Encaja bien en arquitecturas de pagos interbancarios y back-office de compensación.

# Observaciones

Aunque no es específico de tarjetas de crédito, es esencial para la parte de comunicación con cámaras externas. Conviene usarlo como dominio de integración operativa con la red y no como dominio del negocio de la tarjeta en sí.

# Referencias

- BIAN Service Landscape V13.0 Value Chain View
- BIAN ACH Operations Service Domain