---
title: "Fraud Detection Service"
knowledge_domain: building_blocks
source_type: "markdown_curated"
document_name: "fraud-detection"
version: "1.1"
language: "es"
summary: "Evalúa riesgo de fraude en tiempo real usando scoring y patrones."
tags:
  - building-block
  - fraude
source_url: ""
author: "arquitectura"
last_reviewed: "2026-04-09"
status: draft
---

# Descripción general

Motor de evaluación de riesgo que analiza transacciones en tiempo real utilizando reglas y modelos analíticos.

# Propósito

Detectar y prevenir transacciones fraudulentas antes de su ejecución.

# Alineamiento BIAN

Service Domain: Fraud Evaluation  
CR: FraudCase  
BQ:
- RiskAssessment
- PatternAnalysis
- AlertManagement

# Interfaces

- API REST:
  - POST /fraud/evaluate
- Eventos:
  - FraudDetected
  - FraudCleared

# Capacidades

- Scoring en tiempo real
- Evaluación por geolocalización
- Detección de anomalías
- Integración con listas negras

# Escenarios de uso

- Transacciones con tarjeta
- Transferencias de alto monto

# Dependencias

- Customer Behavior Data
- Transaction History

# Riesgos

- Falsos positivos (impacto cliente)
- Latencia en decisiones

# Referencias

- BIAN Fraud Evaluation