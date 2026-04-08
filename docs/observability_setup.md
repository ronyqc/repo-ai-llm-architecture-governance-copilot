# Observabilidad del MVP

## Objetivo de la observabilidad

La capa mínima de observabilidad del proyecto Architecture Governance Copilot tiene como objetivo habilitar la recolección y centralización de telemetría operativa para el MVP. Esta base permitirá analizar el comportamiento de la aplicación, revisar eventos relevantes y preparar la integración progresiva del backend y del pipeline con los servicios de monitoreo de Azure.

En esta etapa, la observabilidad se limita al aprovisionamiento de los recursos base requeridos para Application Insights y Log Analytics. La integración completa con el backend y con el pipeline será abordada en tareas posteriores.

## Recursos aprovisionados

Los recursos aprovisionados para la capa mínima de observabilidad del MVP son:

- Resource group: rg-agc-data-dev
- Log Analytics workspace: law-agc-dev
- Application Insights: appi-agc-dev

Application Insights fue creado como recurso asociado al workspace de Log Analytics, permitiendo que la telemetría recolectada se almacene y consulte desde el entorno centralizado de análisis.

## Configuración base

La configuración base considera un esquema mínimo para la fase MVP:

- Uso del resource group rg-agc-data-dev como contenedor de los recursos de observabilidad.
- Uso del workspace law-agc-dev como repositorio central para logs y telemetría.
- Uso de Application Insights appi-agc-dev como punto de captura y análisis de telemetría aplicativa.
- Asociación de Application Insights con el workspace de Log Analytics.

Esta configuración deja disponible la infraestructura necesaria para que los componentes del proyecto puedan enviar telemetría cuando se implemente la integración correspondiente.

## Relación entre Application Insights y Log Analytics

Application Insights appi-agc-dev está asociado al workspace law-agc-dev. Esta relación permite que los datos de telemetría de la aplicación se almacenen en Log Analytics y puedan ser consultados de forma centralizada.

Para el MVP, esta asociación establece la base de observabilidad sin asumir que todos los componentes de la solución ya están enviando métricas, trazas o eventos. El recurso queda preparado para integraciones posteriores desde el backend y desde los procesos de despliegue.

## Uso esperado en la arquitectura

En la arquitectura del MVP, Application Insights se utilizará como el servicio de observabilidad aplicativa para capturar información relevante del comportamiento del sistema. Log Analytics actuará como el workspace central donde se consolidará la telemetría generada.

El uso esperado incluye la futura recolección de señales como eventos de aplicación, trazas, errores y métricas operativas. En esta etapa, la capa queda aprovisionada como dependencia de infraestructura, pero no se considera todavía una integración funcional completa con el backend ni con el pipeline.

## Relación con siguientes tareas

Las siguientes tareas deberán completar la integración de la observabilidad con los componentes del proyecto. Entre ellas se consideran:

- Configurar el backend para enviar telemetría hacia Application Insights.
- Definir qué eventos, trazas y errores deben registrarse durante la ejecución del MVP.
- Incorporar variables o secretos necesarios para conectar la aplicación con Application Insights.
- Evaluar la integración de validaciones o pasos de observabilidad dentro del pipeline.
- Documentar consultas operativas básicas sobre el workspace de Log Analytics cuando exista telemetría disponible.

Estas tareas deben ejecutarse sin crear recursos adicionales que no estén justificados por la evolución del MVP.