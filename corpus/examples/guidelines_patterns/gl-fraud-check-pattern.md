---
title: "Patrón de Evaluación de Fraude en Línea"
knowledge_domain: guidelines_patterns
source_type: "markdown_curated"
document_name: "fraud-check-pattern"
version: "1.1"
language: "es"
summary: "Integra evaluación antifraude en tiempo real."
tags:
  - guideline
source_url: ""
author: "arquitectura"
last_reviewed: "2026-04-09"
status: draft
---

# Descripción

Define cómo integrar evaluación antifraude en el flujo de pagos.

# Problema

Riesgo de fraude en transacciones.

# Recomendación

- Evaluación síncrona antes de ejecución
- Scoring basado en reglas + ML

# Cuándo aplica

- Tarjetas
- Pagos alto monto

# Cuándo no aplica

- Pagos de bajo riesgo

# Impacto arquitectónico

- Incrementa latencia
- Reduce fraude

# Ejemplo

Pago → scoring → decisión → continuar/rechazar

# Buenas prácticas

- cache de decisiones
- segmentación por riesgo

# Anti-patrones

- fraude solo batch
- no integrar con orquestador

# Métricas

- tasa fraude detectado
- falsos positivos

# Referencias

- BIAN Fraud Evaluation