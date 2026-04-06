# Objetivo del servicio Azure AI Search

El servicio Azure AI Search cumple el rol de vector store del MVP de "Architecture Governance Copilot" dentro de la arquitectura RAG del proyecto. Su propósito es almacenar chunks de conocimiento indexados para habilitar recuperación semántica por similitud vectorial, filtrado por dominio y trazabilidad hacia la fuente original.

En esta fase, el servicio constituye la base de recuperación de conocimiento, pero todavía no participa en un flujo completo de ingestión ni consulta desde backend. La implementación actual se enfoca en dejar preparada la infraestructura mínima necesaria para las siguientes tareas del MVP.

# Configuración del servicio

El servicio Azure AI Search fue aprovisionado en el resource group `rg-agc-data-dev`, que corresponde a la capa de datos e inteligencia del proyecto.

Información registrada para este componente:

- resource group: `rg-agc-data-dev`
- nombre del servicio: `srch-agc-dev`
- tier utilizado: `Basic`
- región: `Central US`


# Definición del índice

El índice creado para el MVP se llama `idx-agc-knowledge-dev`.

Su propósito es almacenar conocimiento segmentado del proyecto para soportar recuperación relevante en escenarios RAG. Cada registro del índice representa un chunk de documento, no un documento completo. Esta decisión permite trabajar con unidades de contenido más precisas, mejorar la recuperación y mantener trazabilidad hacia el origen documental.

El índice sigue el esquema lógico definido previamente en la tarea T4 y fue preparado para combinar búsqueda textual, filtros estructurados y evolución hacia retrieval vectorial.

# Campos del índice

Los campos principales definidos para el índice son los siguientes:

- `id`: identificador único del registro indexado.
- `content`: texto principal del chunk que será base de recuperación.
- `title`: título descriptivo asociado al contenido o al documento origen.
- `knowledge_domain`: dominio lógico del conocimiento para segmentación y filtrado.
- `source_type`: tipo de fuente desde la cual proviene el contenido.
- `source_url`: referencia o ubicación de la fuente original.
- `document_name`: nombre del documento desde el cual se generó el chunk.
- `chunk_order`: posición secuencial del chunk dentro del documento.
- `metadata`: metadatos serializados para enriquecimiento y contexto adicional.
- `updated_at`: fecha y hora de actualización del registro.
- `chunk_id`: identificador estable del chunk para trazabilidad y reprocesamiento.

Desde una perspectiva funcional, estos campos se organizan en tres grupos principales:

- campos de contenido: `content` y `title`, orientados a representar la información recuperable.
- campos de filtro: `knowledge_domain`, `source_type`, `document_name`, `chunk_order` y `updated_at`, orientados a restringir o segmentar resultados.
- campos de trazabilidad: `id`, `chunk_id`, `source_url` y `metadata`, orientados a preservar referencia, contexto y relación con la fuente original.

Esta estructura es consistente con el diseño del MVP porque permite mantener simplicidad operativa sin perder capacidad de evolución hacia consultas más precisas y respuestas con fuentes.

# Configuración de búsqueda vectorial

El índice fue configurado con un campo vectorial llamado `content_vector`.

La configuración aplicada es la siguiente:

- campo vectorial: `content_vector`
- tipo: `Collection(Edm.Single)`
- dimensión: `1536`
- algoritmo: `HNSW`
- métrica: `cosine`

Además, se configuró un vector search profile basado en HNSW con métrica cosine, alineado con el uso previsto de embeddings de dimensión 1536 para el MVP.

Esta configuración permite realizar búsqueda semántica por similitud, comparando la cercanía entre el embedding de una consulta y los embeddings almacenados para cada chunk dentro del índice.

# Relación con la arquitectura

Este componente se conecta directamente con varias piezas de la arquitectura definida para el proyecto.

- `T6` chunking: el proceso de chunking definirá cómo se fragmenta cada documento antes de indexarlo, generando los registros que poblarán `content`, `chunk_id` y `chunk_order`.
- `T23` Azure OpenAI: este componente proveerá los embeddings que se almacenarán en `content_vector` para habilitar retrieval vectorial.
- `T26` ingestión: el flujo de ingestión será responsable de transformar documentos fuente en chunks, generar metadata y cargar registros al índice.
- `T24` query: el backend consultará Azure AI Search para recuperar chunks relevantes que luego alimentarán la respuesta del copilot.

Dentro de la arquitectura general, Azure AI Search funciona como la capa de recuperación de conocimiento estructurado y vectorial sobre la que se apoyará el patrón RAG del MVP.

# Notas para siguientes tareas

Este servicio será utilizado en las siguientes tareas del proyecto:

- `T23`: generación de embeddings y alineamiento con el campo `content_vector`.
- `T24`: integración del backend de consulta con el índice `idx-agc-knowledge-dev`.
- `T26`: ingestión documental para poblar el índice con chunks y metadata.

La implementación actual deja resuelta la base de infraestructura del motor de búsqueda para el MVP, pero las capacidades de carga y consulta todavía dependen de la ejecución de esas tareas posteriores.
