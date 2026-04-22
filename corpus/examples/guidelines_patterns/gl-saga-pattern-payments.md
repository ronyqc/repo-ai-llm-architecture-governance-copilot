---
title: "Patrón Saga para Pagos Distribuidos"
knowledge_domain: guidelines_patterns
source_type: "markdown_curated"
document_name: "saga-pattern-payments"
version: "1.1"
language: "es"
summary: "Implementa consistencia eventual en pagos distribuidos."
tags:
  - guideline
source_url: ""
author: "arquitectura"
last_reviewed: "2026-04-09"
status: draft
---

# Descripción

Patrón para coordinar transacciones distribuidas mediante pasos y compensaciones.

# Problema

No existe transacción global entre:
- Core Banking
- Switch
- Sistemas externos

# Recomendación

Implementar:
- Saga orquestada (recomendado en banca)
- Eventos para transición de estado
- Acciones compensatorias

# Cuándo aplica

- Transferencias interbancarias
- Pagos con múltiples sistemas

# Cuándo no aplica

- Sistemas monolíticos

# Impacto arquitectónico

- Introduce consistencia eventual
- Reduce necesidad de rollback global

# Ejemplo

1. Debitar cuenta  
2. Autorizar tarjeta  
3. Ejecutar pago  

Si falla paso 3 → revertir paso 1

# Buenas prácticas

- Definir compensaciones explícitas
- Evitar side effects irreversibles

# Anti-patrones

- Mezclar saga con transacciones ACID
- No definir rollback

# Métricas

- ratio de compensación
- tiempo de resolución de saga

# Referencias

- Saga Pattern