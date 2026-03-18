# osysHome Object Model

This document describes the core object model used throughout osysHome, explains the hierarchy, inheritance, API, and provides practical examples for smart home automation.

---

## Concept

The osysHome object model is an **object-oriented runtime database**. Unlike a traditional flat key-value store, it provides:

- **Classes** — typed blueprints that define structure (properties, methods, templates)
- **Objects** — named instances of classes that hold actual values
- **Inheritance** — classes extend other classes, objects inherit all class properties and methods
- **Live Values** — every property has a current value, change timestamp, and full history
- **Methods** — Python scripts that execute inside the osysHome runtime, with arguments, return values, and scheduling

This model is the backbone of automation: sensors update properties via `setProperty()`, automations react via method calls, and the Dashboard renders objects using their Jinja2 templates.

---

## Hierarchy

```
Class
  ├── parent_id → Class (inheritance chain)
  ├── Properties (class-level)
  │    ├── type, params, validation
  │    └── method_id → Method
  ├── Methods (class-level Python code)
  ├── Template (Jinja2 HTML for Dashboard)
  └── Objects[]
       ├── Properties (object-level overrides)
       ├── Methods (object-level overrides)
       ├── Values[]  (current property values)
       │    ├── name, value, source, changed
       │    └── History[]  (historical values)
       └── Tasks[]  (scheduled jobs)
```

---

## Classes

A **Class** is a blueprint. It defines:

- **Properties** — what data fields every object of this class has
- **Methods** — what Python code every object of this class can run
- **Template** — how to render a summary widget for the Dashboard

Classes support **single inheritance**: a class can have one parent class and will inherit all its properties and methods.

### Example Class: `Sensor`

```
Class: Sensor
  Properties:
    - temperature  (float, min=-50, max=100, decimals=1)
    - humidity     (float, min=0, max=100, decimals=0)
    - battery      (int, min=0, max=100, unit=%)
    - last_seen    (datetime)
    - online       (bool)
  Methods:
    - refresh()    → queries the device for fresh values
```

All objects of class `Sensor` automatically have these 5 properties and the `refresh` method.

---

## Objects

An **Object** is a named instance. It:

- Has a unique name (no spaces, no dots) — e.g. `BedroomSensor`
- May belong to a Class (and thus inherits its properties and methods)
- Stores current **Values** for each property in the database
- May define **object-level overrides** for properties and methods
- May have its own additional properties not in the class

### Example Objects

```
Object: BedroomSensor  (class: Sensor)
  Values:
    BedroomSensor.temperature = 22.5   (set 2025-11-15 08:30:00, source: z2m)
    BedroomSensor.humidity    = 45     (set 2025-11-15 08:30:00, source: z2m)
    BedroomSensor.battery     = 87
    BedroomSensor.online      = True

Object: KitchenSensor  (class: Sensor)
  Values:
    KitchenSensor.temperature = 24.1
    KitchenSensor.humidity    = 60
    KitchenSensor.battery     = 52
    KitchenSensor.online      = True
```

---

## Properties

A **Property** is a typed field defined either at class level or at object level.

### Property Types

| Type | Description | Example values |
|---|---|---|
| `bool` | Boolean | `True`, `False` |
| `int` | Integer | `22`, `100`, `-5` |
| `float` | Decimal number | `22.5`, `0.75` |
| `str` | String / text | `"on"`, `"auto"` |
| `datetime` | Date + time | `2025-11-15 08:30:00` |
| `enum` | Predefined set of keys | `"0"`, `"1"`, `"2"` |
| `dict` | JSON dictionary | `{"mode": "cool", "temp": 22}` |
| `list` | JSON array | `["red", "green", "blue"]` |

### Property Params (metadata)

Each property carries a JSON `params` field for validation and display:

```json
{
  "min": 0,
  "max": 100,
  "step": 0.5,
  "decimals": 1,
  "default_value": 20,
  "read_only": false,
  "allowed_values": [16, 18, 20, 22, 24],
  "regexp": "^[a-z]+$",
  "enum_values": {"0": "Off", "1": "Cool", "2": "Heat", "3": "Fan"},
  "rate_limit": 5.0,
  "icon": "mdi:thermometer",
  "color": "#2196f3",
  "sort_order": 10,
  "depends_on": {"property": "online", "value": true, "condition": "equals"}
}
```

---

## Inheritance

When a class inherits from a parent class, all parent properties and methods are available in child classes and their objects — without storing duplicates.

```
Class: Device
  Properties: name, online, last_seen

Class: Sensor (parent: Device)
  Properties: temperature, humidity   ← PLUS name, online, last_seen from Device

Class: TemperatureSensor (parent: Sensor)
  Properties: high_temp_alert         ← PLUS all Sensor + Device properties
```

An object of class `TemperatureSensor` will have: `name`, `online`, `last_seen`, `temperature`, `humidity`, `high_temp_alert` — all 6 properties.

### Object-level overrides

An object can **redefine** a property or method to have custom behavior different from the class definition. This creates an object-level property record that shadows the class property for that specific object.

---

## API: Accessing Object Values

The runtime API is available inside Python method code, automation scripts, and plugins.

### `getProperty(path)` → value

Returns the current value of a property.

```python
temperature = getProperty("BedroomSensor.temperature")
# → 22.5 (float)

is_online = getProperty("BedroomSensor.online")
# → True (bool)

mode = getProperty("Thermostat.mode")
# → "cool" (str)
```

### `setProperty(path, value, source=None)` → None

Sets the value of a property. Triggers:

1. Validation against the property's params (min/max/regexp/allowed_values/etc.)
2. Rate limiting (if `rate_limit` configured)
3. History recording (if `history > 0` configured)
4. WebSocket broadcast `changeProperty` event to all connected clients
5. Execution of the property's linked method (if `method_id` configured)

```python
setProperty("BedroomSensor.temperature", 23.1, source="manual")
setProperty("KitchenLight.brightness", 80)
setProperty("Thermostat.mode", "heat", source="automation")
```

### `callMethod(path, args=None, source=None)` → result

Calls a method on an object or class.

```python
result = callMethod("BedroomSensor.refresh")
# → None or return value of the method's Python code

result = callMethod("Thermostat.setTemperature", args={"target": 21})
# → whatever the method returns
```

---

## Value Object

The `Value` model stored in the database:

| Field | Type | Description |
|---|---|---|
| `object_id` | int | Which object owns this value |
| `name` | str | Property name |
| `value` | str | Current value (stored as string, cast on read) |
| `source` | str | Who last set this value (plugin name, "manual", etc.) |
| `changed` | datetime | When the value was last changed (UTC) |
| `linked` | str | Comma-separated list of linked properties |

### History

If `property.history > 0`, every change is recorded in the `History` table:

| Field | Type |
|---|---|
| `value_id` | int |
| `value` | str |
| `source` | str |
| `changed` | datetime (UTC) |

History is viewable at `HistoryView?name=<propName>&object=<objectId>`.

---

## Methods

A **Method** is a named Python code block. It can be defined at class level (shared by all objects) or at object level (specific to one object).

### Method execution context

Inside the method code, the following globals are available:

- `self` — the object instance (from ObjectsStorage)
- `getProperty(path)` — read any property
- `setProperty(path, value)` — write any property
- `callMethod(path, args)` — call any method
- All standard Python builtins

### Example method

```python
# Method: Thermostat.autoSetTemperature
# Adjusts target temperature based on time of day

import datetime
hour = datetime.datetime.now().hour

if 6 <= hour < 9 or 17 <= hour < 22:
    target = 22  # Active hours
else:
    target = 18  # Night / away

setProperty("Thermostat.target_temperature", target, source="autoSetTemperature")
```

---

## Object Templates

Each class and object can have a **Jinja2 HTML template** used to render a compact widget card on the Dashboard.

### Example template

```html
{# Template for Sensor class #}
<div class="d-flex gap-2 align-items-center flex-wrap">
  <span title="Temperature">
    <iconify-icon icon="mdi:thermometer"></iconify-icon>
    {{ object.temperature.value | round(1) }} °C
  </span>
  <span title="Humidity">
    <iconify-icon icon="mdi:water-percent"></iconify-icon>
    {{ object.humidity.value }} %
  </span>
  <span title="Battery">
    <iconify-icon icon="mdi:battery"></iconify-icon>
    {{ object.battery.value }} %
  </span>
</div>
```

Templates support Jinja2 template inheritance: a child class template can extend the parent class template using `{% extends "ParentClass" %}`.

---

## Schedules / Tasks

Objects can have **Task** entries that run Python code at a scheduled time or on a cron schedule.

```python
# Task: BedroomSensor_temperature_nightly_check
# Crontab: 0 23 * * *  (every night at 23:00)

temp = getProperty("BedroomSensor.temperature")
if temp > 25:
    callMethod("Ventilation.start")
```

Tasks are stored in the `Task` table with:

| Field | Description |
|---|---|
| `name` | Unique task name |
| `code` | Python code to execute |
| `crontab` | Cron expression (periodic) |
| `runtime` | Next execution datetime (UTC) |
| `expire` | Deadline for one-shot tasks |
| `active` | Enable/disable toggle |

---

## Integration with Other Plugins

### z2m (Zigbee2MQTT)

When a Zigbee device pairs, z2m creates an Object named after the device. Properties are created for each device attribute (e.g. `temperature`, `occupancy`, `battery`). The plugin calls `setProperty()` on every MQTT message received.

### Tuya

Same pattern: each Tuya device becomes an Object. The plugin maps Tuya DPS codes to property names and calls `setProperty()` on state updates.

### MQTT

Generic MQTT subscriptions can map topic payloads to object properties via configurable rules.

### Dashboard

The Dashboard plugin reads object templates and renders them as widget cards. WebSocket events (`changeProperty`) update property values in real time without page refresh.

### Automations / Scripts

Any Python code in the system can use `getProperty()`, `setProperty()`, and `callMethod()` to interact with any object regardless of which plugin created it.

---

## Complete Example: Smart Thermostat

```
Class: Thermostat
  Properties:
    - current_temperature  (float, read_only: true)
    - target_temperature   (float, min=10, max=35, step=0.5)
    - mode                 (enum, enum_values: {0:"Off", 1:"Heat", 2:"Cool", 3:"Auto"})
    - heating_active       (bool, read_only: true)
    - schedule_enabled     (bool)
  Methods:
    - apply_schedule()     → sets target_temperature based on time of day
    - emergency_stop()     → sets mode to 0 (Off)
  Template: shows current temp, target temp, mode badge

Object: LivingRoomThermostat  (class: Thermostat)
  Values:
    LivingRoomThermostat.current_temperature = 21.3   (source: z2m)
    LivingRoomThermostat.target_temperature  = 22.0   (source: manual)
    LivingRoomThermostat.mode                = "1"    (Heat)
    LivingRoomThermostat.heating_active      = True
    LivingRoomThermostat.schedule_enabled    = True
  Task: LivingRoomThermostat_apply_schedule  (crontab: 0 */1 * * *)
```

Automation script (runs when window sensor opens):
```python
# Turn off heating when window is open
setProperty("LivingRoomThermostat.mode", "0", source="window_sensor")
```

---

## Database Schema (Summary)

```
classes (id, name, description, parent_id, template)
    ↳ properties (id, class_id, object_id, name, type, params, method_id, history)
    ↳ methods (id, class_id, object_id, name, description, code, call_parent)

objects (id, name, description, class_id, template)
    ↳ values (id, object_id, name, value, source, changed, linked)
        ↳ history (id, value_id, value, source, changed)
    ↳ tasks (id, name, code, crontab, runtime, expire, active)
```

All property access goes through `ObjectsStorage` — an in-memory cache that keeps parsed object instances ready for fast read/write without constant database queries.
