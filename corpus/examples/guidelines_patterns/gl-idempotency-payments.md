---
title: "Patrón de Idempotencia en Pagos"
knowledge_domain: guidelines_patterns
source_type: "markdown_curated"
document_name: "idempotency-payments"
version: "1.1"
language: "es"
summary: "Previene duplicidad de pagos en sistemas distribuidos."
tags:
  - guideline
source_url: ""
author: "arquitectura"
last_reviewed: "2026-04-09"
status: draft
---

# Descripción

Garantiza que múltiples ejecuciones de una misma operación produzcan un único resultado.

# Problema

Reintentos por:
- timeouts
- fallas de red
pueden generar pagos duplicados.

# Recomendación

- Generar idempotency_key por transacción
- Persistir resultado asociado
- Validar antes de procesar

# Cuándo aplica

- APIs de pagos
- Integraciones externas

# Cuándo no aplica

- Operaciones batch controladas

# Impacto arquitectónico

- Requiere almacenamiento adicional
- Mejora resiliencia

# Ejemplo

POST /payments con mismo key → devuelve misma respuesta

# Buenas prácticas

- TTL para keys
- incluir hash de payload

# Anti-patrones

- generar key en backend
- no persistir respuesta

# Métricas

- duplicados evitados
- reintentos exitosos

# Referencias

- Payment API design