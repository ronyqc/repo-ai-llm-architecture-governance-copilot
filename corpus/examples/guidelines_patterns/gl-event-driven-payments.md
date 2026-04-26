---
title: "Patrón Event-Driven para Pagos"
knowledge_domain: guidelines_patterns
source_type: "markdown_curated"
document_name: "event-driven-payments"
version: "1.1"
language: "es"
summary: "Desacopla servicios de pagos mediante eventos."
tags:
  - guideline
source_url: ""
author: "arquitectura"
last_reviewed: "2026-04-09"
status: draft
---

# Descripción

Arquitectura donde servicios se comunican mediante eventos.

# Problema

Acoplamiento fuerte entre servicios.

# Recomendación

- Usar broker (Kafka/EventHub)
- Publicar eventos de dominio
- Consumidores independientes

# Cuándo aplica

- Pagos complejos
- Integraciones múltiples

# Cuándo no aplica

- Flujos de baja latencia crítica

# Impacto arquitectónico

- Alta escalabilidad
- Complejidad en consistencia

# Ejemplo

PaymentCompleted → Notification + Settlement

# Buenas prácticas

- eventos inmutables
- versionado de eventos

# Anti-patrones

- eventos con lógica
- dependencia síncrona

# Métricas

- lag de consumidores
- throughput de eventos

# Referencias

- Event-driven architecture