# FAQ Interno — Equipo de Ingeniería

## Onboarding

**¿Cómo solicito accesos a los repositorios internos?**
Debes crear un ticket en el portal de IT con la categoría "Accesos > Repositorios"
indicando el nombre del repositorio y tu rol en el proyecto. La aprobación la
realiza el líder técnico del equipo dueño del repositorio.

**¿Dónde encuentro las credenciales de los entornos de desarrollo?**
Las credenciales de desarrollo se gestionan mediante Vault interno
(`vault.technova.local`). Nunca deben compartirse por Slack ni correo.

## Despliegues

**¿Cuál es la ventana de despliegue permitida?**
Los despliegues a producción solo pueden realizarse de lunes a jueves, entre
las 9:00 y las 16:00 hora local, salvo hotfixes críticos aprobados por el
Gerente de Ingeniería.

**¿Qué hago si un despliegue falla?**
El pipeline de CI/CD realiza rollback automático si las pruebas de humo
posteriores al despliegue fallan. Si el rollback automático no funciona, se debe
ejecutar `deploy-cli rollback --env=prod --to=<version_anterior>` manualmente.

## Buenas prácticas de datos internos (RAG)

**¿Qué documentos internos se pueden usar para alimentar un sistema RAG?**
Únicamente documentación pública interna (manuales, políticas, FAQs) clasificada
como "Uso Interno". Documentos con información de clientes o datos personales
deben pasar primero por el proceso de anonimización del equipo de Datos.

**¿Con qué frecuencia se deben reindexar los documentos en la base vectorial?**
Se recomienda reindexar cada vez que un documento fuente cambie, o como mínimo
una vez por semana mediante el job programado `reindex-knowledge-base`.
