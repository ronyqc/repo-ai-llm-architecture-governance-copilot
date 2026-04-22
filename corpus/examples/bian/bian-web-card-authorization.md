---
title: "Card Authorization"
knowledge_domain: bian
source_type: "markdown_curated"
document_name: "bian-web-card-authorization"
version: "1.0"
language: "es"
summary: "Service Domain BIAN encargado de la decisión en tiempo real de autorización de transacciones con tarjeta."
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

Card Authorization es el dominio BIAN que realiza la evaluación en tiempo real de una transacción de tarjeta antes de su aprobación o rechazo. Centraliza la lógica de decisión para autorizar compras, retiros u otras operaciones iniciadas con tarjeta de crédito o cargo.

# Propósito de negocio

Mitigar riesgo y asegurar control transaccional en línea, verificando que la transacción cumple condiciones financieras, operativas y de seguridad antes de permitir su ejecución.

# Capacidades principales

- Decisión de autorización en tiempo real para transacciones de tarjeta.
- Verificación del dispositivo y del medio de pago usado.
- Autenticación del tarjetahabiente.
- Validaciones de crédito, fraude y mecanismos stand-in.
- Soporte para evaluación desde la perspectiva de issuer, network o acquirer.

# Relación con otros dominios

Recibe insumos desde Card Transaction Capture y canales/terminales. Se relaciona con Credit Card como dominio del producto, con Fraud Evaluation para controles de riesgo, con Card Transaction Switch para routing, y con dominios de límite, cliente y cuenta cuando la arquitectura los incorpora.

# Aplicabilidad en arquitectura

Es clave en arquitecturas de autorización online, issuer authorization platforms, autorizadores integrados con red de marca, e-commerce payments, POS acquiring y validaciones previas a clearing/settlement.

# Observaciones

Debe diseñarse con requisitos estrictos de baja latencia y alta disponibilidad. No conviene mezclarlo con funciones de clearing o settlement; su foco es la decisión online. En escenarios de alta criticidad, suele desplegarse con patrones resilientes y capacidades de stand-in.

# Referencias

- BIAN Service Landscape V13.0 Value Chain View
- BIAN Card Authorization Service Domain