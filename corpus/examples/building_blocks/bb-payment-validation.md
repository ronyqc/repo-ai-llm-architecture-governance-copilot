---
title: "Payment Validation Service"
knowledge_domain: building_blocks
source_type: "markdown_curated"
document_name: "payment-validation"
version: "1.1"
language: "es"
summary: "Valida reglas regulatorias, operativas y de negocio para pagos."
tags:
  - building-block
  - validacion
source_url: ""
author: "arquitectura"
last_reviewed: "2026-04-09"
status: draft
---

# Descripción general

Servicio que valida la integridad, elegibilidad y cumplimiento de reglas antes de ejecutar una transacción.

# Propósito

Reducir errores operativos y evitar procesamiento de pagos inválidos o no autorizados.

# Alineamiento BIAN

Service Domain: Payment Order  
CR: PaymentOrder  
BQ:
- Validation
- ComplianceCheck
- EligibilityCheck

# Interfaces

- API REST:
  - POST /payments/validate
- Eventos:
  - PaymentValidated
  - PaymentRejected

# Capacidades

- Validación de formato (CCI, PAN, IBAN)
- Validación de saldo y cuenta activa
- Validación regulatoria (listas negras, AML básico)
- Validación de canal y límites operativos

# Escenarios de uso

- Transferencias interbancarias
- Pagos con tarjeta

# Dependencias

- Customer Profile
- Core Banking

# Riesgos

- Reglas desactualizadas vs regulación
- Dependencia de sistemas core

# Referencias

- BIAN Payment Order