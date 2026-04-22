---
title: "Limit Management Service"
knowledge_domain: building_blocks
source_type: "markdown_curated"
document_name: "limit-management"
version: "1.1"
language: "es"
summary: "Gestiona límites de crédito y transacción."
tags:
  - building-block
source_url: ""
author: "arquitectura"
last_reviewed: "2026-04-09"
status: draft
---

# Descripción general

Servicio que administra límites financieros de clientes.

# Propósito

Controlar exposición de riesgo.

# Alineamiento BIAN

Service Domain: Customer Credit Limit  
CR: CreditLimit  
BQ:
- LimitAllocation
- LimitCheck
- LimitAdjustment

# Capacidades

- Validación de cupo disponible
- Actualización en tiempo real
- Gestión de sobregiros

# Escenarios de uso

- Tarjetas
- Transferencias

# Dependencias

- Customer Profile

# Riesgos

- Inconsistencia de límites