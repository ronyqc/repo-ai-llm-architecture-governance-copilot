# E3-3.9 Resultados de Prueba de Carga

## Objetivo

Validar el comportamiento del endpoint `/api/v1/query` bajo carga concurrente, utilizando el despliegue en la nube.

## Configuración de la prueba

- Herramienta: k6
- Backend: Azure Container Apps
- Endpoint: `/api/v1/query`
- Usuarios virtuales: 10
- Duración: 1 minuto
- Autenticación: JWT Bearer Token
- Tipo de carga: consultas RAG contra Azure AI Search + Azure OpenAI

## Resumen de resultados

- Total de solicitudes: 286
- Solicitudes exitosas: 40
- Solicitudes rechazadas por rate limiting: 246
- Tasa de error reportada por k6: 86.01%
- Latencia p95 global: 6.3 segundos
- Latencia p95 de solicitudes exitosas: 6.95 segundos
- Respuestas HTTP 429 observadas: Sí

## Interpretación

La prueba de carga fue ejecutada con el mínimo requerido de 10 usuarios concurrentes.

El sistema no falló por caídas de la aplicación ni por indisponibilidad de infraestructura. La mayoría de las solicitudes fallidas corresponden a respuestas HTTP 429 generadas por la política de control de tasa (rate limiting) del backend:

`Se excedió el límite de solicitudes para /query. Intenta nuevamente más tarde.`

Este comportamiento es esperado y forma parte del mecanismo de protección de la API frente a un exceso de solicitudes.

Las solicitudes exitosas retornaron HTTP 200, respuestas válidas y fuentes provenientes del pipeline RAG.

## Conclusión

El sistema responde correctamente bajo acceso concurrente y aplica control de rate limiting ante picos de carga.

Para soportar mayor concurrencia sostenida, se recomienda en futuras versiones:

- Ajustar la política de rate limiting
- Incrementar las réplicas del backend
- Revisar la capacidad (throughput) de Azure OpenAI

## Evidencias

- `reports/load_test_results.json`
- Ejecución en consola con respuestas HTTP 200 y HTTP 429