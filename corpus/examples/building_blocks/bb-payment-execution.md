---
title: "Payment Execution Service"
knowledge_domain: building_blocks
source_type: "markdown_curated"
document_name: "payment-execution"
version: "1.1"
language: "es"
summary: "Ejecuta pagos hacia redes externas bancarias."
tags:
  - building-block
source_url: ""
author: "arquitectura"
last_reviewed: "2026-04-09"
status: draft
---

# Descripción general

Servicio encargado de enviar instrucciones de pago a redes externas.

# Propósito

Materializar la transferencia de fondos entre entidades financieras.

# Alineamiento BIAN

Service Domain: Payment Execution  
CR: PaymentInstruction  
BQ:
- Execution
- Routing
- Confirmation

# Interfaces

- API REST:
  - POST /payments/execute
- Integraciones:
  - ACH / Cámara compensación
- Eventos:
  - PaymentSent
  - PaymentConfirmed

# Capacidades

- Enrutamiento por red
- Gestión de estados externos
- Confirmación asincrónica

# Escenarios de uso

- Transferencias interbancarias

# Dependencias

- External Payment Network

# Riesgos

- Fallas de red externa