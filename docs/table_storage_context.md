# Table Storage Context - Architecture Governance Copilot

## Objetivo del almacenamiento de contexto

Azure Table Storage se utiliza para mantener el historial conversacional por sesión en el MVP de Architecture Governance Copilot.

El almacenamiento de contexto permite persistir los turnos de conversación asociados a una sesión, de modo que el backend pueda recuperar interacciones previas y usarlas como contexto operativo durante la generación de respuestas.

En esta fase MVP, el objetivo es contar con un mecanismo simple, trazable y de bajo acoplamiento para registrar consultas del usuario, respuestas del asistente y metadatos mínimos de ejecución.

## Configuración del recurso

La configuración base del recurso de almacenamiento de contexto es la siguiente:

- Resource group: rg-agc-data-dev
- Storage account: storage account creado para contexto conversacional
- Tipo de servicio: Azure Table Storage
- Fase del proyecto: MVP

El storage account debe estar disponible para el backend del proyecto y debe usarse exclusivamente según el alcance definido para el almacenamiento de contexto conversacional del MVP.

## Tabla creada

La tabla creada para almacenar el historial conversacional es ConversationHistory.

El propósito de esta tabla es registrar los turnos de conversación generados durante una sesión, manteniendo una estructura consultable por identificador de sesión y orden cronológico de interacción.

ConversationHistory actúa como el repositorio operativo del contexto conversacional mínimo requerido por el copiloto durante el MVP.

## Convención de claves

La tabla ConversationHistory utiliza la siguiente convención de claves:

- PartitionKey = session_id
- RowKey = turno correlativo, por ejemplo turn_000001, turn_000002, turn_000003

El uso de session_id como PartitionKey permite agrupar todos los turnos pertenecientes a una misma conversación dentro de una única partición lógica. Esto facilita la recuperación del historial de una sesión sin mezclar interacciones de otros usuarios o conversaciones.

El uso de turnos correlativos como RowKey permite conservar el orden lógico de la conversación y recuperar los eventos de una sesión de forma secuencial. La convención turn_000001 mantiene orden lexicográfico y evita problemas de ordenamiento cuando la cantidad de turnos crece.

Esta convención es adecuada para el MVP porque prioriza simplicidad, trazabilidad y recuperación directa del contexto por sesión.

## Estructura mínima del historial

Cada registro de ConversationHistory debe contener, como mínimo, los siguientes campos:

- user_query: consulta enviada por el usuario.
- assistant_answer: respuesta generada por el asistente.
- created_at: fecha y hora de creación del turno.
- trace_id: identificador de trazabilidad asociado a la ejecución.
- knowledge_domain: dominio de conocimiento utilizado o clasificado para la interacción.
- sources_json: referencias o fuentes usadas durante la respuesta, serializadas como JSON.
- tokens_used: cantidad de tokens consumidos durante la interacción.
- latency_ms: latencia de procesamiento medida en milisegundos.

Estos campos permiten auditar el comportamiento básico del copiloto, reconstruir el contexto de una sesión y analizar el desempeño operativo durante el MVP.

## Uso en arquitectura

Azure Table Storage participa en la arquitectura como almacenamiento operacional del contexto conversacional.

Su uso principal es la recuperación de contexto por sesión. Antes de generar una nueva respuesta, el backend puede consultar los turnos previos asociados al session_id para incorporar información conversacional relevante.

La integración con el backend debe mantenerse acotada al registro y recuperación del historial conversacional necesario para el flujo del MVP.

El historial almacenado también sirve como soporte para RAG, ya que permite combinar el contexto conversacional reciente con la información recuperada desde las fuentes de conocimiento del proyecto. Azure Table Storage no reemplaza el índice de búsqueda ni la base documental, sino que complementa el flujo manteniendo memoria conversacional por sesión.

## Notas para siguientes tareas

- Definir la estrategia de contexto para el MVP, considerando si se usarán los últimos turnos, un resumen de conversación o una combinación de ambos.
- Validar el número máximo de turnos que el backend recuperará por session_id en cada interacción.
- Integrar el uso de ConversationHistory con T26 para coordinar el contexto conversacional con el flujo RAG.
- Integrar el uso de ConversationHistory con T33 para alinear trazabilidad, métricas y persistencia del historial conversacional.
- Revisar la política de retención del historial conversacional para entornos posteriores al MVP.
