---
title: "Card Authorization Service"
knowledge_domain: building_blocks
source_type: "markdown_curated"
document_name: "card-authorization"
version: "1.1"
language: "es"
summary: "Autoriza transacciones de tarjeta validando fondos, límites y riesgo."
tags:
  - building-block
  - tarjetas
source_url: ""
author: "arquitectura"
last_reviewed: "2026-04-09"
status: draft
---

# Descripción general

Servicio que procesa solicitudes de autorización de tarjetas en tiempo real.

# Propósito

Asegurar que las transacciones cumplan condiciones antes de aprobarse.

# Alineamiento BIAN

Service Domain: Card Authorization  
CR: CardTransaction  
BQ:
- AuthorizationCheck
- LimitCheck
- RiskCheck

# Interfaces

- API REST:
  - POST /cards/authorize
- Integraciones:
  - Visa / Mastercard
- Eventos:
  - AuthorizationApproved
  - AuthorizationDeclined

# Capacidades

- Validación de límite de crédito
- Verificación de estado de tarjeta
- Autorización en milisegundos
- Soporte para tokenización

# Escenarios de uso

- POS
- E-commerce

# Dependencias

- Limit Management
- Fraud Detection

# Riesgos

- Latencia crítica
- Dependencia de redes externas

# Referencias

- BIAN Card Authorization