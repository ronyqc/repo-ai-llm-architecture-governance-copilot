---
title: "Patrón de Orquestación de Pagos (Payment Orchestration Pattern)"
knowledge_domain: guidelines_patterns
source_type: "markdown_curated"
document_name: "payment-orchestration-pattern"
version: "1.1"
language: "es"
summary: "Define cómo implementar un orquestador robusto para flujos de pagos complejos."
tags:
  - guideline
  - arquitectura
  - pagos
source_url: ""
author: "arquitectura"
last_reviewed: "2026-04-09"
status: draft
---

# Descripción

Patrón que establece el uso de un componente central que coordina el flujo completo de pagos, gestionando estados y dependencias entre servicios.

# Problema

Los pagos implican múltiples pasos (validación, fraude, autorización, ejecución). Sin orquestación:
- lógica duplicada
- falta de trazabilidad
- errores difíciles de recuperar

# Recomendación

Implementar un orquestador basado en:
- máquina de estados (state machine)
- persistencia de estado
- manejo de errores con compensaciones

Decisiones clave:
- síncrono vs asíncrono (recomendado híbrido)
- persistencia (DB transaccional o event store)
- control de idempotencia

# Cuándo aplica

- Pagos interbancarios
- Flujos con múltiples sistemas

# Cuándo no aplica

- Operaciones simples (ej. consulta de saldo)

# Impacto arquitectónico

- Introduce un componente crítico
- Mejora gobernanza del flujo
- Permite observabilidad end-to-end

# Ejemplo

Flujo:
1. INIT
2. VALIDATED
3. FRAUD_CHECKED
4. AUTHORIZED
5. EXECUTED
6. COMPLETED

# Buenas prácticas

- Usar correlation_id por transacción
- Manejar retry con backoff exponencial
- Persistir estado en cada transición

# Anti-patrones

- Orquestador con lógica de negocio pesada
- Dependencia síncrona en todos los pasos

# Métricas

- Latencia por estado
- tasa de fallos por paso
- tasa de compensaciones

# Referencias

- BIAN Payment Execution
- Saga Pattern