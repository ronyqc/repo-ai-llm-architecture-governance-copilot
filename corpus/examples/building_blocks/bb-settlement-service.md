---
title: "Settlement Service"
knowledge_domain: building_blocks
source_type: "markdown_curated"
document_name: "settlement-service"
version: "1.1"
language: "es"
summary: "Gestiona liquidación y conciliación financiera."
tags:
  - building-block
source_url: ""
author: "arquitectura"
last_reviewed: "2026-04-09"
status: draft
---

# Descripción general

Servicio encargado de reconciliar y liquidar transacciones.

# Propósito

Garantizar consistencia financiera entre sistemas.

# Alineamiento BIAN

Service Domain: Clearing and Settlement  
CR: SettlementTransaction  
BQ:
- Reconciliation
- Netting
- Settlement

# Capacidades

- Conciliación automática
- Liquidación batch
- Manejo de diferencias

# Escenarios de uso

- Liquidación de tarjetas
- ACH

# Dependencias

- Core contable

# Riesgos

- Descuadres contables