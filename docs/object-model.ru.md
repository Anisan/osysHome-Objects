# Объектная модель osysHome

Этот документ описывает основную объектную модель osysHome, объясняет иерархию, наследование, API и приводит практические примеры для автоматизации умного дома.

---

## Концепция

Объектная модель osysHome — это **объектно-ориентированная база данных времени выполнения**. В отличие от обычного хранилища «ключ-значение», она предоставляет:

- **Классы** — типизированные шаблоны, определяющие структуру (свойства, методы, шаблоны отображения)
- **Объекты** — именованные экземпляры классов, хранящие реальные значения
- **Наследование** — классы расширяют другие классы, объекты наследуют все свойства и методы класса
- **Живые значения** — каждое свойство имеет текущее значение, временную метку изменения и полную историю
- **Методы** — Python-скрипты, выполняемые в среде выполнения osysHome, с аргументами, возвращаемыми значениями и планированием

Эта модель является основой автоматизации: сенсоры обновляют свойства через `setProperty()`, автоматизации реагируют через вызовы методов, Dashboard отображает объекты через Jinja2-шаблоны.

---

## Иерархия

```
Класс
  ├── parent_id → Класс (цепочка наследования)
  ├── Свойства (на уровне класса)
  │    ├── тип, параметры, валидация
  │    └── method_id → Метод
  ├── Методы (Python-код на уровне класса)
  ├── Шаблон (Jinja2 HTML для Dashboard)
  └── Объекты[]
       ├── Свойства (переопределения на уровне объекта)
       ├── Методы (переопределения на уровне объекта)
       ├── Значения[]  (текущие значения свойств)
       │    ├── name, value, source, changed
       │    └── История[]  (исторические значения)
       └── Задачи[]  (запланированные задания)
```

---

## Классы

**Класс** — это шаблон. Он определяет:

- **Свойства** — какие поля данных имеет каждый объект этого класса
- **Методы** — какой Python-код может выполнять каждый объект этого класса
- **Шаблон** — как отображать объект на Dashboard

Классы поддерживают **одиночное наследование**: класс может иметь одного родителя и унаследует все его свойства и методы.

### Пример класса: `Sensor`

```
Класс: Sensor
  Свойства:
    - temperature  (float, min=-50, max=100, decimals=1)
    - humidity     (float, min=0, max=100, decimals=0)
    - battery      (int, min=0, max=100)
    - last_seen    (datetime)
    - online       (bool)
  Методы:
    - refresh()    → запрашивает устройство для получения свежих значений
```

Все объекты класса `Sensor` автоматически имеют эти 5 свойств и метод `refresh`.

---

## Объекты

**Объект** — именованный экземпляр. Он:

- Имеет уникальное имя (без пробелов и точек) — например: `BedroomSensor`
- Может принадлежать классу (наследует его свойства и методы)
- Хранит текущие **Значения** для каждого свойства в базе данных
- Может определять **переопределения** свойств и методов на уровне объекта
- Может иметь собственные дополнительные свойства, не входящие в класс

### Примеры объектов

```
Объект: BedroomSensor  (класс: Sensor)
  Значения:
    BedroomSensor.temperature = 22.5   (установлено 2025-11-15 08:30:00, источник: z2m)
    BedroomSensor.humidity    = 45     (установлено 2025-11-15 08:30:00, источник: z2m)
    BedroomSensor.battery     = 87
    BedroomSensor.online      = True

Объект: KitchenSensor  (класс: Sensor)
  Значения:
    KitchenSensor.temperature = 24.1
    KitchenSensor.humidity    = 60
    KitchenSensor.battery     = 52
    KitchenSensor.online      = True
```

---

## Свойства

**Свойство** — это типизированное поле, определённое на уровне класса или объекта.

### Типы свойств

| Тип | Описание | Примеры значений |
|---|---|---|
| `bool` | Булево | `True`, `False` |
| `int` | Целое число | `22`, `100`, `-5` |
| `float` | Десятичное число | `22.5`, `0.75` |
| `str` | Строка / текст | `"on"`, `"auto"` |
| `datetime` | Дата + время | `2025-11-15 08:30:00` |
| `enum` | Предопределённый набор ключей | `"0"`, `"1"`, `"2"` |
| `dict` | JSON-словарь | `{"mode": "cool", "temp": 22}` |
| `list` | JSON-массив | `["red", "green", "blue"]` |

### Параметры свойства (метаданные)

Каждое свойство содержит JSON-поле `params` для валидации и отображения:

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
  "enum_values": {"0": "Выкл", "1": "Охлаждение", "2": "Нагрев", "3": "Авто"},
  "rate_limit": 5.0,
  "icon": "mdi:thermometer",
  "color": "#2196f3",
  "sort_order": 10,
  "depends_on": {"property": "online", "value": true, "condition": "equals"}
}
```

---

## Наследование

Когда класс наследует от родительского класса, все свойства и методы родителя доступны в дочерних классах и их объектах — без дублирования в базе данных.

```
Класс: Device
  Свойства: name, online, last_seen

Класс: Sensor (родитель: Device)
  Свойства: temperature, humidity  ← ПЛЮС name, online, last_seen от Device

Класс: TemperatureSensor (родитель: Sensor)
  Свойства: high_temp_alert        ← ПЛЮС все свойства Sensor + Device
```

Объект класса `TemperatureSensor` будет иметь: `name`, `online`, `last_seen`, `temperature`, `humidity`, `high_temp_alert` — все 6 свойств.

### Переопределения на уровне объекта

Объект может **переопределить** свойство или метод для настройки поведения, отличного от определения класса. Это создаёт запись свойства на уровне объекта, которая перекрывает свойство класса только для данного объекта.

---

## API: Доступ к значениям объектов

API времени выполнения доступен внутри кода методов, скриптов автоматизации и плагинов.

### `getProperty(path)` → значение

Возвращает текущее значение свойства.

```python
temperature = getProperty("BedroomSensor.temperature")
# → 22.5 (float)

is_online = getProperty("BedroomSensor.online")
# → True (bool)

mode = getProperty("Thermostat.mode")
# → "cool" (str)
```

### `setProperty(path, value, source=None)` → None

Устанавливает значение свойства. Запускает:

1. Валидацию по параметрам свойства (min/max/regexp/allowed_values и т.д.)
2. Ограничение частоты (если настроен `rate_limit`)
3. Запись в историю (если `history > 0`)
4. WebSocket-трансляцию события `changeProperty` всем подключённым клиентам
5. Выполнение связанного метода свойства (если настроен `method_id`)

```python
setProperty("BedroomSensor.temperature", 23.1, source="manual")
setProperty("KitchenLight.brightness", 80)
setProperty("Thermostat.mode", "heat", source="automation")
```

### `callMethod(path, args=None, source=None)` → результат

Вызывает метод объекта или класса.

```python
result = callMethod("BedroomSensor.refresh")
# → None или возвращаемое значение метода

result = callMethod("Thermostat.setTemperature", args={"target": 21})
# → то, что вернёт метод
```

---

## Объект Value

Модель `Value`, хранимая в базе данных:

| Поле | Тип | Описание |
|---|---|---|
| `object_id` | int | Какому объекту принадлежит это значение |
| `name` | str | Имя свойства |
| `value` | str | Текущее значение (хранится как строка, приводится при чтении) |
| `source` | str | Кто последний установил значение (имя плагина, "manual" и т.д.) |
| `changed` | datetime | Когда значение было последний раз изменено (UTC) |
| `linked` | str | Список связанных свойств через запятую |

### История

Если `property.history > 0`, каждое изменение записывается в таблицу `History`:

| Поле | Тип |
|---|---|
| `value_id` | int |
| `value` | str |
| `source` | str |
| `changed` | datetime (UTC) |

История доступна по адресу `HistoryView?name=<имяСвойства>&object=<idОбъекта>`.

---

## Методы

**Метод** — именованный блок Python-кода. Может быть определён на уровне класса (общий для всех объектов) или на уровне объекта (специфичный для одного объекта).

### Контекст выполнения метода

Внутри кода метода доступны следующие глобальные переменные:

- `self` — экземпляр объекта (из ObjectsStorage)
- `getProperty(path)` — прочитать любое свойство
- `setProperty(path, value)` — записать любое свойство
- `callMethod(path, args)` — вызвать любой метод
- Все стандартные встроенные функции Python

### Пример метода

```python
# Метод: Thermostat.autoSetTemperature
# Устанавливает целевую температуру в зависимости от времени суток

import datetime
hour = datetime.datetime.now().hour

if 6 <= hour < 9 or 17 <= hour < 22:
    target = 22  # Активные часы
else:
    target = 18  # Ночь / отсутствие

setProperty("Thermostat.target_temperature", target, source="autoSetTemperature")
```

---

## Шаблоны объектов

Каждый класс и объект может иметь **Jinja2 HTML-шаблон** для отображения виджета-карточки на Dashboard.

### Пример шаблона

```html
{# Шаблон для класса Sensor #}
<div class="d-flex gap-2 align-items-center flex-wrap">
  <span title="Температура">
    <iconify-icon icon="mdi:thermometer"></iconify-icon>
    {{ object.temperature.value | round(1) }} °C
  </span>
  <span title="Влажность">
    <iconify-icon icon="mdi:water-percent"></iconify-icon>
    {{ object.humidity.value }} %
  </span>
  <span title="Батарея">
    <iconify-icon icon="mdi:battery"></iconify-icon>
    {{ object.battery.value }} %
  </span>
</div>
```

Шаблоны поддерживают наследование Jinja2: шаблон дочернего класса может расширять шаблон родительского класса через `{% extends "РодительскийКласс" %}`.

---

## Расписания / Задачи

Объекты могут иметь записи **Task**, выполняющие Python-код в запланированное время или по cron-расписанию.

```python
# Задача: BedroomSensor_temperature_nightly_check
# Crontab: 0 23 * * *  (каждую ночь в 23:00)

temp = getProperty("BedroomSensor.temperature")
if temp > 25:
    callMethod("Ventilation.start")
```

Задачи хранятся в таблице `Task`:

| Поле | Описание |
|---|---|
| `name` | Уникальное имя задачи |
| `code` | Python-код для выполнения |
| `crontab` | Cron-выражение (периодическое) |
| `runtime` | Следующее время выполнения (UTC) |
| `expire` | Дедлайн для разовых задач |
| `active` | Переключатель включения/отключения |

---

## Интеграция с другими плагинами

### z2m (Zigbee2MQTT)

При сопряжении Zigbee-устройства z2m создаёт Object с именем устройства. Свойства создаются для каждого атрибута устройства (например: `temperature`, `occupancy`, `battery`). Плагин вызывает `setProperty()` при каждом MQTT-сообщении.

### Tuya

Аналогичная схема: каждое устройство Tuya становится Object. Плагин сопоставляет коды DPS с именами свойств и вызывает `setProperty()` при обновлении состояния.

### MQTT

Общие MQTT-подписки могут сопоставлять данные из топиков со свойствами объектов через настраиваемые правила.

### Dashboard

Плагин Dashboard читает шаблоны объектов и отображает их как виджет-карточки. WebSocket-события (`changeProperty`) обновляют значения свойств в реальном времени без перезагрузки страницы.

### Автоматизации / Скрипты

Любой Python-код в системе может использовать `getProperty()`, `setProperty()` и `callMethod()` для взаимодействия с любым объектом, независимо от того, какой плагин его создал.

---

## Полный пример: Умный термостат

```
Класс: Thermostat
  Свойства:
    - current_temperature  (float, read_only: true)
    - target_temperature   (float, min=10, max=35, step=0.5)
    - mode                 (enum, enum_values: {0:"Выкл", 1:"Нагрев", 2:"Охлаждение", 3:"Авто"})
    - heating_active       (bool, read_only: true)
    - schedule_enabled     (bool)
  Методы:
    - apply_schedule()     → устанавливает target_temperature по времени суток
    - emergency_stop()     → устанавливает mode в 0 (Выкл)
  Шаблон: показывает текущую температуру, целевую температуру, бейдж режима

Объект: LivingRoomThermostat  (класс: Thermostat)
  Значения:
    LivingRoomThermostat.current_temperature = 21.3   (источник: z2m)
    LivingRoomThermostat.target_temperature  = 22.0   (источник: manual)
    LivingRoomThermostat.mode                = "1"    (Нагрев)
    LivingRoomThermostat.heating_active      = True
    LivingRoomThermostat.schedule_enabled    = True
  Задача: LivingRoomThermostat_apply_schedule  (crontab: 0 */1 * * *)
```

Скрипт автоматизации (запускается при открытии датчика окна):
```python
# Отключить нагрев при открытом окне
setProperty("LivingRoomThermostat.mode", "0", source="window_sensor")
```

---

## Схема базы данных (краткая)

```
classes (id, name, description, parent_id, template)
    ↳ properties (id, class_id, object_id, name, type, params, method_id, history)
    ↳ methods (id, class_id, object_id, name, description, code, call_parent)

objects (id, name, description, class_id, template)
    ↳ values (id, object_id, name, value, source, changed, linked)
        ↳ history (id, value_id, value, source, changed)
    ↳ tasks (id, name, code, crontab, runtime, expire, active)
```

Весь доступ к свойствам проходит через `ObjectsStorage` — кэш в памяти, хранящий разобранные экземпляры объектов для быстрого чтения/записи без постоянных запросов к базе данных.
