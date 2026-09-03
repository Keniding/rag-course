# Política de Soporte Técnico — TechNova S.A.

## 1. Niveles de servicio (SLA)

| Prioridad | Descripción                                  | Tiempo de primera respuesta | Tiempo de resolución objetivo |
|-----------|-----------------------------------------------|------------------------------|--------------------------------|
| P1        | Servicio caído en producción                  | 15 minutos                   | 4 horas                        |
| P2        | Degradación importante del servicio           | 1 hora                        | 1 día hábil                    |
| P3        | Error menor sin impacto crítico               | 4 horas hábiles               | 5 días hábiles                 |
| P4        | Consulta general o solicitud de mejora        | 1 día hábil                   | Sin compromiso formal           |

## 2. Canales de contacto

- **Portal de soporte**: para tickets P2, P3 y P4.
- **Línea de guardia (on-call)**: exclusiva para incidentes P1, disponible 24/7.
- **Slack `#soporte-clientes`**: consultas rápidas no urgentes.

## 3. Proceso de escalamiento

1. El ticket es asignado automáticamente al equipo correspondiente según la categoría.
2. Si no hay respuesta dentro del tiempo de primera respuesta, el ticket escala
   automáticamente al líder técnico del área.
3. Los incidentes P1 activan un canal de guerra ("war room") y notifican al
   Gerente de Operaciones de forma inmediata.

## 4. Mantenimientos programados

Los mantenimientos programados se comunican con al menos 5 días hábiles de
anticipación a través del portal de estado (`status.technova.com`) y por correo
a los administradores de cada cuenta. Los mantenimientos de emergencia pueden
comunicarse con menor anticipación, priorizando la estabilidad del servicio.

## 5. Política de reembolsos por incumplimiento de SLA

Si TechNova incumple el SLA de un ticket P1, el cliente puede solicitar un
crédito de servicio equivalente al 5% de la facturación mensual por cada hora
de incumplimiento, con un tope del 30% de la facturación mensual.
