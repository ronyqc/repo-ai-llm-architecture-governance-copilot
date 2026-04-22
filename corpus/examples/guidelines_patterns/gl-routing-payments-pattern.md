---
title: "Patrón de Routing de Pagos"
knowledge_domain: guidelines_patterns
source_type: "markdown_curated"
document_name: "routing-payments-pattern"
version: "1.1"
language: "es"
summary: "Define cómo enrutar pagos dinámicamente."
tags:
  - guideline
source_url: ""
author: "arquitectura"
last_reviewed: "2026-04-09"
status: draft
---

# Descripción

Permite dirigir pagos a distintas redes.

# Problema

Múltiples redes (ACH, tarjetas).

# Recomendación

- motor de reglas
- configuración dinámica

# Cuándo aplica

- multired

# Cuándo no aplica

- red única

# Impacto arquitectónico

- flexibilidad
- complejidad

# Ejemplo

CCI → ACH  
Tarjeta → Visa

# Buenas prácticas

- reglas versionadas
- fallback routing

# Anti-patrones

- hardcode routing

# Métricas

- tasa de error por red

# Referencias

- BIAN Payment Routing