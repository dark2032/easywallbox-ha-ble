# easyWallbox BLE — conexión por Bluetooth (v0.1.1, experimental)

Integración personalizada para conectar Home Assistant directamente a la
**Free2move / eSolutions easyWallbox por BLE sin ESP32**.

> **Prototipo no validado contra hardware real.** Esta entrega se centra en
> comprobar el enlace y leer un registro, sin enviar ninguna orden que
> modifique intensidad, configuración DPM o inicio/parada.

## Qué comprueba el asistente

1. Home Assistant cuenta con un escáner Bluetooth **con capacidad de conectar**.
2. Detecta por BLE la MAC indicada (lista de detectados o entrada manual).
3. Puede establecer conexión GATT.
4. El dispositivo presenta los UUID GATT del cargador.
5. Acepta el PIN de autorización `A:` del QR mediante `$BLE,AUTH,...`.
6. Responde a una **lectura** de registro (`174`, intensidad límite).

Si falla una etapa, el formulario muestra el avance de las anteriores.
Elige entre **automático**, **directo** o **solicitar emparejamiento del SO**.
Ninguna opción omite la autorización A:.

⚠️ **Importante con los dos códigos**:

- `A:` PIN de autorización de la aplicación/protocolo de easyWallbox. Lo solicita el formulario.
- `P:` *passkey* Bluetooth del emparejamiento **del sistema operativo**.
  La opción «emparejar» de esta versión pide al SO que inicie el proceso,
  pero **no sabe suministrar automáticamente P:**; en Linux/BlueZ puede
  necesitar un agente externo o un emparejamiento previo en el SO.
  Por tanto, puede fallar incluso con la clave P: correcta.

BLE no es Wi-Fi: la máquina Home Assistant debe disponer de un adaptador
BLE cercano al equipo o un proxy BLE con conexión bidireccional.
Un proxy que solo retransmite anuncios **no** es suficiente.

## Instalación y actualización

- GitHub: `https://github.com/dark2032/easywallbox-ha-ble`.
- HA 2026.11+: Marketplace → Añadir desde enlace → URL del repositorio.
  Para versiones anteriores con HACS: repositorio personalizado (Integration).
- Actualizar, reiniciar Home Assistant. Para ejecutar el **nuevo asistente de
  prueba** si ya tenías una entrada creada en 0.1.0, elimínala y vuelve a
  añadir esta integración (antes guarda MAC y A: localmente).
- El PIN A: se guarda en la configuración privada de Home Assistant: no lo
  publiques en GitHub, capturas o incidencias.

### VirtualBox

La tarjeta BT integrada de un ordenador Windows **no suele estar expuesta**
a la máquina virtual. Pasar un **dongle Bluetooth USB** a la VM (USB
passthrough) y confirmar que Home Assistant lo reconoce en
Ajustes → Dispositivos y servicios → Bluetooth. No basta con que Windows
lo detecte. También se puede utilizar un proxy Bluetooth compatible con
conexión activa, sujeto a las limitaciones de emparejamiento.

### Primeras pruebas del cliente

1. Cerrar la aplicación Free2move (una conexión BLE activa a la vez).
2. Verificar el Bluetooth de **su** Home Assistant y que alcance al cargador.
3. Elegir MAC detectada o introducirla; introducir `A:`, **no `P:`**.
4. Elegir **Automático** y ejecutar la comprobación.
5. Si falla, anotar la **primera etapa fallida**, sin compartir PIN.
   Repetir con «Solicitar emparejamiento del sistema operativo» si procede.
6. Si aparece error relacionado con agente/clave P:, revisar emparejamiento
   de BlueZ. No probar PINes al azar ni alterar la configuración eléctrica.

## Estado

- ✅ Estructura de integración HA + publicación por Marketplace/HACS.
- ✅ Implementado control escalonado del diagnóstico y test de lectura.
- 🧪 Sin pruebas reales de BLE o emparejamiento P:.
- ⛔ Controles de **escritura de intensidad deshabilitados en la UI** hasta
  validar las lecturas sobre el cargador.
- ⛔ No implementa parar/reanudar ni cambia el DPM.

Basado en las investigaciones públicas de
[paolofaz](https://github.com/paolofaz/Easywallbox---Esphome) y
[Pawel188](https://github.com/Pawel188/free2move-easy-wallbox-esphome-Home-Assistant).
