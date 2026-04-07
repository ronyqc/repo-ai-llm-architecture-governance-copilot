# Azure OpenAI Setup - Architecture Governance Copilot

## Objetivo del servicio

Azure OpenAI provee las capacidades de generación de lenguaje natural y generación de embeddings para el MVP de Architecture Governance Copilot.

El servicio se utiliza para soportar dos capacidades principales:

- Procesamiento y generación de respuestas del copiloto mediante un modelo LLM.
- Vectorización de contenido técnico y documental mediante embeddings compatibles con Azure AI Search.

En esta fase MVP, el servicio debe mantenerse enfocado en habilitar los flujos mínimos de consulta, recuperación aumentada por generación y gobierno arquitectónico asistido.

## Configuración del recurso

El recurso de Azure OpenAI debe aprovisionarse con la siguiente configuración base:

- Resource group: rg-agc-data-dev
- Nombre del recurso: aoai-agc-dev
- Entorno: desarrollo
- Fase del proyecto: MVP

El recurso debe quedar disponible para ser consumido por los componentes backend del proyecto y por los flujos que integran Azure AI Search como índice de recuperación documental.

## Deployment LLM

El deployment principal para generación de lenguaje debe configurarse con el modelo gpt-4.1.

Este deployment será utilizado por el backend del copiloto para:

- Interpretar consultas del usuario.
- Generar respuestas contextualizadas.
- Apoyar tareas de análisis de arquitectura.
- Integrarse con los resultados recuperados desde Azure AI Search.

El nombre del deployment debe mantenerse consistente con la configuración de variables de entorno del proyecto para evitar divergencias entre infraestructura, documentación y runtime de la aplicación.

## Deployment embeddings

El deployment de embeddings debe configurarse con el modelo text-embedding-3-large.

Este deployment será utilizado para generar representaciones vectoriales del contenido documental que alimenta la experiencia de búsqueda semántica y recuperación contextual del MVP.

El deployment de embeddings debe ser compatible con la configuración del índice vectorial en Azure AI Search.

## Configuración de dimensiones (1536)

El modelo text-embedding-3-large debe configurarse para generar embeddings de 1536 dimensiones.

Esta configuración es obligatoria para mantener compatibilidad con Azure AI Search en el MVP, dado que el índice vectorial debe usar la misma dimensionalidad que los vectores generados por Azure OpenAI.

La dimensión configurada debe mantenerse alineada entre:

- Deployment de embeddings en Azure OpenAI.
- Pipeline de ingesta y vectorización.
- Definición del campo vectorial en Azure AI Search.
- Configuración de la aplicación backend.

Cualquier cambio futuro en la dimensionalidad requiere actualizar de forma coordinada el deployment, el índice de búsqueda y los procesos de ingesta.

## Variables de entorno

El proyecto debe incluir variables de entorno para conectar el backend con el recurso Azure OpenAI y sus deployments.

Las variables deben cubrir como mínimo:

- Endpoint del recurso Azure OpenAI aoai-agc-dev.
- API key o mecanismo de autenticación definido para el entorno de desarrollo.
- Nombre del deployment LLM basado en gpt-4.1.
- Nombre del deployment de embeddings basado en text-embedding-3-large.
- Dimensionalidad de embeddings configurada en 1536.
- Versión de API de Azure OpenAI utilizada por la aplicación.

Estas variables deben mantenerse sincronizadas entre el archivo de ejemplo de configuración, el entorno local de desarrollo y la configuración usada por despliegues posteriores.

## Relación con arquitectura (T22, T23, T26)

- T22: Azure AI Search, donde se almacenará el índice vectorial.
- T23: Azure OpenAI, que provee generación y embeddings.
- T26: procesamiento documental y generación de chunks/embeddings para poblar el índice.

La configuración documentada en este archivo debe considerarse como la referencia técnica para alinear infraestructura, aplicación y búsqueda vectorial durante el MVP.

## Notas para siguientes tareas

integrar backend con Azure OpenAI
usar deployment gpt-4.1 para generación
usar deployment text-embedding-3-large con dimensión 1536 para embeddings
mantener consistencia entre .env, .env.example, AI Search y pipeline de ingesta