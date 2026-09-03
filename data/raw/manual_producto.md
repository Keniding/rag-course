# Manual de Producto — NovaCloud Backup

## 1. Descripción general

NovaCloud Backup es el servicio interno de respaldo en la nube de TechNova S.A.
Permite a los equipos de ingeniería programar copias de seguridad automáticas
de bases de datos, buckets de almacenamiento y volúmenes de máquinas virtuales.

## 2. Planes disponibles

| Plan | Almacenamiento | Retención | Regiones | Cifrado |
|------|-----------------|-----------|----------|---------|
| Starter | 100 GB | 7 días | 1 | AES-256 |
| Business | 1 TB | 30 días | 3 | AES-256 |
| Enterprise | Ilimitado | Hasta 365 días (configurable) | Multi-región | AES-256 + llaves propias (BYOK) |

## 3. Instalación del agente

1. Descargar el agente `novacloud-agent` desde el portal interno.
2. Ejecutar `novacloud-agent init --token <TOKEN_DE_LA_ORGANIZACION>`.
3. Configurar el archivo `backup.yaml` con las rutas o bases de datos a respaldar.
4. Verificar el estado con `novacloud-agent status`.

## 4. Política de reintentos

Si un backup falla, el agente reintenta automáticamente hasta 3 veces con un
retroceso exponencial de 5, 15 y 45 minutos. Si los 3 intentos fallan, se genera
una alerta en el canal `#alerts-backup` y se abre un ticket automático en el
sistema de soporte.

## 5. Restauración de datos

La restauración se realiza desde el portal web seleccionando el snapshot deseado.
El tiempo estimado de restauración depende del tamaño:

- Menos de 50 GB: aproximadamente 10 minutos.
- Entre 50 GB y 500 GB: aproximadamente 45 minutos.
- Más de 500 GB: se recomienda contactar al equipo de soporte para una
  restauración asistida, ya que puede tardar varias horas.

## 6. Preguntas frecuentes de configuración

**¿Puedo cambiar de plan sin perder mis backups?**
Sí, el cambio de plan es inmediato y no afecta los backups existentes, siempre
que el nuevo plan tenga capacidad suficiente para almacenarlos.

**¿Los backups están cifrados?**
Sí, todos los planes incluyen cifrado AES-256 en reposo y TLS 1.3 en tránsito.
El plan Enterprise permite además usar llaves de cifrado propias (BYOK).
