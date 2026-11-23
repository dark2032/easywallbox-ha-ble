# Publicación en GitHub e instalación desde Home Assistant

> **ANTES DE PUBLICAR:** sustituye `TU_USUARIO` por tu usuario u organización de GitHub en
> `custom_components/easywallbox_ble/manifest.json` (campos `documentation` e `issue_tracker`).
> El repositorio debe ser **público** para que lo instale Home Assistant Marketplace o HACS.
>
> **Aviso:** prototipo para pruebas. No confirmado con una easyWallbox real; la escritura de corriente
> no debe habilitarse sobre una instalación de un cliente sin supervisión y comprobaciones eléctricas.

## Instalar desde la UI: Home Assistant 2026.11 y posteriores

1. Crear un repositorio público de GitHub, p. ej. `easywallbox-ha-ble`.
2. Subir los **archivos de la raíz de este proyecto** (no el ZIP como único archivo):
   `hacs.json`, `README.md` y la carpeta `custom_components/`, entre otros.
3. En Home Assistant abrir **Ajustes → Marketplace → Add from link / Añadir desde enlace**.
4. Introducir `https://github.com/TU_USUARIO/easywallbox-ha-ble` y añadirlo. La primera vez
   puede pedir vincular GitHub; no da acceso a repositorios privados.
5. Abrir el repositorio y elegir **Instalar**. La primera instalación con flujo de configuración
   puede abrir el asistente directamente. En actualizaciones posteriores reiniciar Home Assistant.
6. Configurar dirección MAC BLE, PIN de autorización `A:` y límite máximo de amperios.

## Home Assistant anterior a 2026.11

Si la instalación todavía tiene **HACS**: HACS → menú de tres puntos → Repositorios personalizados
→ pegar la URL de GitHub → categoría `Integration` → Añadir → descargar, reiniciar
Home Assistant y añadir la integración en **Ajustes → Dispositivos y servicios**.

## Publicar cambios para que los pruebe otra instalación

- Mantener `main` como rama de desarrollo y publicar versiones identificadas, por ejemplo
  `v0.1.0`, `v0.1.1`, etc. Para cada versión, cambiar también `version` en
  `custom_components/easywallbox_ble/manifest.json`.
- Crear la correspondiente **Release** en GitHub, explicando cambios y riesgos.
- La persona que tenga el cargador podrá ver una actualización en Home Assistant, descargarla
  y **reiniciar Home Assistant**; no se aplica automáticamente al guardar cambios en GitHub.
- Marketplace comprueba repositorios personalizados periódicamente (aprox. cada 48 h); las
  actualizaciones no son necesariamente inmediatas. Para iteraciones muy rápidas se puede
  copiar manualmente `custom_components/easywallbox_ble/` y reiniciar en un equipo de pruebas.
- No subir códigos `A:`, `P:`, MAC de clientes, registros con información privada ni el QR completo.

## Limitaciones importantes

- **BLE en máquina virtual:** los adaptadores Bluetooth del PC host no aparecen automáticamente
  en Home Assistant virtualizado. Se necesita pasar un adaptador USB BLE a la VM o disponer
  de un proxy BLE; para conexión directa, un adaptador USB pasado a la VM es lo más sencillo.
- El PIN `A:` autoriza operaciones en el cargador, pero **no sustituye** el emparejamiento
  cifrado Bluetooth del SO (posible clave `P:`). La integración aún **NO** realiza este pairing.
- Hay que probar físicamente conexión, lecturas, unidades y límites de corriente. El proyecto
  no tiene todavía pausa/reanudación ni control de carga por PVPC.
- No alterar ni anular la pinza DPM. Validar con un profesional el comportamiento del DPM
  cuando hay instalaciones solares que exportan energía a la red.

---

# easyWallbox BLE — integración directa experimental para Home Assistant

**Estado: prototipo v0.1, sin probar contra un cargador real. No instalar aún como solución de producción para un cliente.**

## Qué hace

- Home Assistant ↔ adaptador Bluetooth BLE ↔ Free2move/eSolutions easyWallbox, **sin ESP32**.
- Configuración manual de MAC Bluetooth, PIN de autorización `A:` y límite de corriente permitido.
- Lecturas: estado, intensidad (A), potencia (kW), energía de la sesión (kWh), duración, vehículo conectado, DPM activo, error, límites confirmados.
- Control de **intensidad máxima del coche** (registro 174), en incrementos de 1 A, de 6 A al límite máximo configurado (por defecto 16 A). El valor se comprueba leyendo el registro después de escribirlo.
- **No implementa** encendido/apagado, pausa/reanudación ni escritura del registro DPM 158. No afecta intencionalmente a la pinza ni al balanceo DPM.

## Requisitos

1. Home Assistant compatible con integraciones personalizadas y la integración **Bluetooth** activada.
2. Adaptador Bluetooth BLE con capacidad de **conexión GATT** (integrado o USB). El servidor y el cargador deben estar dentro del alcance.
3. Dirección MAC Bluetooth del cargador, obtenida por escaneo BLE.
4. PIN de autorización, normalmente identificado por `A:` al escanear el QR del cargador. **No es necesariamente el mismo código** que el de emparejamiento Bluetooth (`P:`).
5. El sistema Bluetooth del servidor debe poder establecer la conexión cifrada/emparejada (bonding). **Este prototipo NO automatiza el emparejamiento BLE ni introduce el passkey**: dependiendo del sistema puede requerir un proceso manual en BlueZ/host y tal vez un agente de emparejamiento. Esa es la principal incógnita de las futuras pruebas.

## Instalación de desarrollo

1. Copia `custom_components/easywallbox_ble/` al directorio `config/custom_components/easywallbox_ble/` de Home Assistant.
2. Reinicia Home Assistant.
3. En **Ajustes → Dispositivos y servicios → Añadir integración**, busca **easyWallbox BLE (experimental)**.
4. Introduce MAC, PIN `A:` y máximo permitido en amperios (configura el máximo según instalación, protección, cableado y cargador; no presupongas 32 A).
5. En pruebas, primero verifica las lecturas sin conectar el coche. Después, y solo con el instalador, comprueba la variación del límite de corriente con un vehículo real.

**Importante:** la conexión BLE se abre para cada consulta/orden y se libera después. La wallbox admite una sola conexión Bluetooth a la vez, por lo que la aplicación oficial puede interferir mientras se utiliza. Si Home Assistant no ve la wallbox o el cifrado BLE falla, la integración quedará pendiente de configurar hasta resolver acceso y emparejamiento. Nunca copies el QR completo ni los PIN a registros públicos.

## Entidades esperadas

- Sensores: estado, intensidad de carga, potencia, energía sesión, duración, límites confirmados, potencia DPM.
- Binarios: cargando, vehículo conectado, DPM activo, avería, comunicación reciente.
- Número: intensidad máxima (A) para tarjetas y automaciones.

Ejemplo, tras comprobar el ID real de la entidad:

```yaml
action: number.set_value
target:
  entity_id: number.free2move_easywallbox_intensidad_maxima
data:
  value: 10
```

## Pruebas offline

```bash
python -m unittest discover -s tests -v
python -m compileall -q custom_components
```

## Qué falta antes de producción

- Prueba real de descubrimiento, autenticación, emparejamiento Bluetooth cifrado y lectura de notificaciones con fragmentación.
- Verificación de unidades y campos de telemetría con cargador/contador reales.
- Pruebas de seguridad: desconexión, timeouts, reintentos, comandos concurrentes, limitación de intensidad y coexistencia con la app.
- Confirmar el comportamiento de la pinza DPM con la nueva fotovoltaica, especialmente durante exportación a red.
- Una futura versión podrá añadir pausa/reanudación segura **solo tras validar** la estrategia DPM=0 A del proyecto de referencia.

## Referencias

- [paolofaz/Easywallbox---Esphome](https://github.com/paolofaz/Easywallbox---Esphome) — proyecto de referencia, licencia MIT.
- [Pawel188/free2move-easy-wallbox-esphome-Home-Assistant](https://github.com/Pawel188/free2move-easy-wallbox-esphome-Home-Assistant) — documentación alternativa del protocolo.
- [Home Assistant Bluetooth developer docs](https://developers.home-assistant.io/docs/bluetooth/).

El código de este ZIP es nuevo y experimental; toma del trabajo público previo únicamente los datos de funcionamiento del protocolo necesarios para la interoperabilidad.
