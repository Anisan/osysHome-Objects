# Руководство по расширенным валидациям свойств

## Обзор

В модуле "Objects" теперь доступны 4 новых типа валидации для свойств объектов:

1. **step** (Дискретность) - для int и float
2. **allowed_values** (Разрешенные значения) - для всех типов
3. **rate_limit** (Ограничение частоты) - для всех типов  
4. **depends_on** (Зависимости) - для всех типов

## Как задать параметры

### Через веб-интерфейс

1. Откройте модуль **Objects**
2. Выберите класс или объект
3. Перейдите на вкладку **Properties**
4. Нажмите **Edit** на нужном свойстве или создайте новое
5. Заполните нужные поля в разделах:
   - **Validation Parameters** - базовые параметры (min, max, decimals, regexp)
   - **Advanced Validation** - расширенные параметры (step, allowed_values, rate_limit, depends_on)

### Формат JSON в поле Parameters

Все параметры сохраняются в JSON формате в поле `params`. Вы также можете редактировать JSON напрямую.

---

## 1. Step (Дискретность)

### Описание
Определяет шаг, с которым может изменяться значение. Значение должно быть кратным заданному шагу относительно минимума (или 0).

### Применимо к
- `int`
- `float`

### Параметры
```json
{
  "min": 0,
  "max": 100,
  "step": 10
}
```

### Примеры

**Яркость светодиода (шаг 10%):**
```json
{
  "type": "int",
  "params": {
    "min": 0,
    "max": 100,
    "step": 10
  }
}
```
Разрешенные значения: 0, 10, 20, 30, ..., 100

**Температура термостата (шаг 0.5°C):**
```json
{
  "type": "float",
  "params": {
    "min": 18.0,
    "max": 30.0,
    "step": 0.5,
    "decimals": 1
  }
}
```
Разрешенные значения: 18.0, 18.5, 19.0, 19.5, ..., 30.0

**Пользовательская база:**
```json
{
  "type": "int",
  "params": {
    "min": 5,
    "max": 95,
    "step": 10
  }
}
```
Разрешенные значения: 5, 15, 25, 35, ..., 95

### Веб-интерфейс
- Для **int**: поле "Step (Discreteness)" в разделе валидации
- Для **float**: поле "Step (Discreteness)" рядом с "Decimals"

---

## 2. Allowed Values (Разрешенные значения)

### Описание
Ограничивает свойство только конкретными значениями из списка.

### Применимо к
Все типы кроме `enum` (для enum используйте `enum_values`)

### Параметры
```json
{
  "allowed_values": [1, 2, 3, 5, 10]
}
```

### Примеры

**Приоритет задачи:**
```json
{
  "type": "int",
  "params": {
    "allowed_values": [1, 2, 3, 5, 10]
  }
}
```

**Предустановленные цвета:**
```json
{
  "type": "str",
  "params": {
    "allowed_values": ["red", "green", "blue", "yellow", "white"]
  }
}
```

**Множители скорости:**
```json
{
  "type": "float",
  "params": {
    "allowed_values": [0.5, 1.0, 1.5, 2.0, 2.5]
  }
}
```

**Комбинация со step:**
```json
{
  "type": "int",
  "params": {
    "min": 0,
    "max": 100,
    "step": 10,
    "allowed_values": [10, 20, 30, 50, 100]
  }
}
```
Значения должны соответствовать И step (кратны 10), И быть в списке allowed_values

### Веб-интерфейс
Поле "Allowed Values" в разделе "Advanced Validation"
- Формат: JSON массив `[value1, value2, ...]`

---

## 3. Rate Limit (Ограничение частоты)

### Описание
Устанавливает минимальный интервал времени (в секундах) между изменениями свойства. Защищает от дребезга и чрезмерной нагрузки.

### Применимо к
Все типы

### Параметры
```json
{
  "rate_limit": 5.0
}
```

### Примеры

**Кнопка звонка (защита от дребезга):**
```json
{
  "type": "bool",
  "params": {
    "rate_limit": 2.0
  }
}
```
Можно нажать не чаще раза в 2 секунды

**Датчик движения:**
```json
{
  "type": "bool",
  "params": {
    "rate_limit": 5.0
  }
}
```
Обновление не чаще раза в 5 секунд

**Настройка температуры:**
```json
{
  "type": "float",
  "params": {
    "min": 18.0,
    "max": 30.0,
    "step": 0.5,
    "rate_limit": 10.0
  }
}
```
Изменять можно не чаще раза в 10 секунд

### Обход rate_limit
Для системных операций можно обойти ограничение:
```python
prop_manager.setValue(value, bypass_rate_limit=True)
```

### Веб-интерфейс
Поле "Rate Limit (seconds)" в разделе "Advanced Validation"

---

## 4. Depends On (Зависимости)

### Описание
Определяет условия, при которых можно изменять свойство. Свойство может зависеть от значений других свойств того же объекта.

### Применимо к
Все типы

### Условия (condition)
- `equals` - равно (по умолчанию)
- `not_equals` - не равно
- `greater_than` - больше
- `less_than` - меньше
- `greater_or_equal` - больше или равно
- `less_or_equal` - меньше или равно
- `in` - входит в список
- `not_in` - не входит в список

### Формат

**Одиночная зависимость:**
```json
{
  "property": "имя_свойства",
  "value": "ожидаемое_значение",
  "condition": "equals",
  "error_message": "Пользовательское сообщение (опционально)"
}
```

**Множественные зависимости:**
```json
[
  {"property": "enabled", "value": true},
  {"property": "mode", "value": "manual"}
]
```

### Примеры

**Простая зависимость (equals):**
```json
{
  "type": "int",
  "params": {
    "min": 0,
    "max": 2000,
    "depends_on": {
      "property": "mode",
      "value": "manual",
      "condition": "equals",
      "error_message": "Мощность можно изменять только в ручном режиме"
    }
  }
}
```

**Зависимость от температуры (greater_than):**
```json
{
  "type": "int",
  "params": {
    "min": 0,
    "max": 100,
    "depends_on": {
      "property": "temperature",
      "value": 25.0,
      "condition": "greater_than",
      "error_message": "Вентилятор можно включить только при температуре выше 25°C"
    }
  }
}
```

**Множественные зависимости:**
```json
{
  "type": "int",
  "params": {
    "min": 0,
    "max": 100,
    "depends_on": [
      {
        "property": "enabled",
        "value": true,
        "condition": "equals"
      },
      {
        "property": "mode",
        "value": "manual",
        "condition": "equals"
      }
    ]
  }
}
```
Свойство можно изменить только если enabled=true И mode="manual"

**Проверка вхождения в список:**
```json
{
  "depends_on": {
    "property": "mode",
    "value": ["manual", "auto"],
    "condition": "in"
  }
}
```

### Веб-интерфейс
Поле "Dependencies (depends_on)" в разделе "Advanced Validation"
- Формат: JSON объект или массив объектов

---

## Комбинация валидаций

Можно комбинировать несколько валидаций для достижения сложного поведения:

### Пример: Умный термостат
```json
{
  "type": "float",
  "params": {
    "min": 18.0,
    "max": 30.0,
    "step": 0.5,
    "decimals": 1,
    "allowed_values": [18.0, 18.5, 19.0, 19.5, 20.0, 20.5, 21.0, 21.5, 22.0, 22.5, 23.0, 23.5, 24.0, 24.5, 25.0],
    "rate_limit": 10.0,
    "depends_on": {
      "property": "enabled",
      "value": true,
      "condition": "equals"
    },
    "icon": "thermometer",
    "color": "#FF5722"
  }
}
```

Это свойство:
- ✅ Диапазон: 18-30°C
- ✅ Шаг: 0.5°C
- ✅ Только определенные значения (18.0-25.0°C)
- ✅ Не чаще раза в 10 секунд
- ✅ Только если термостат включен

---

## Порядок валидации

При установке значения проверки выполняются в следующем порядке:

1. ✅ Проверка `read_only`
2. ✅ Проверка `rate_limit`
3. ✅ Преобразование типа
4. ✅ Проверка `min`/`max`
5. ✅ Проверка `step`
6. ✅ Проверка `decimals`
7. ✅ Проверка `regexp` / `enum_values`
8. ✅ Проверка `allowed_values`
9. ✅ Проверка `depends_on`

---

## Сообщения об ошибках

### Step
```
ValueError: Value 37 is not aligned with step 10 (base: 0). 
Allowed values: 0, 10, 20...
```

### Allowed Values
```
ValueError: Value 4 is not in allowed values: [1, 2, 3, 5, 10]
```

### Rate Limit
```
ValueError: Property 'button' can be changed only once per 5.0 seconds. 
Please wait 3.2 more seconds.
```

### Depends On
```
ValueError: Cannot set 'power' to '1500': depends on 'mode' equals 'manual', 
but current value is 'auto'
```

Или с пользовательским сообщением:
```
ValueError: Мощность можно изменять только в ручном режиме
```

---

## Примеры использования

### Пример 1: LED лента с дискретной яркостью

**Создание свойства:**
1. Objects → Выбрать объект → Properties → Add
2. Name: `brightness`
3. Type: `int`
4. Validation Parameters:
   - Min: 0
   - Max: 100
   - Step: 10
5. Additional Parameters:
   - Icon: `lightbulb`
   - Color: `#FFC107`

### Пример 2: Кнопка с защитой от дребезга

**Создание свойства:**
1. Objects → Выбрать объект → Properties → Add
2. Name: `pressed`
3. Type: `bool`
4. Advanced Validation:
   - Rate Limit: 2.0

### Пример 3: Мощность обогревателя с зависимостью

**Создание свойств:**

Сначала создаем свойство `mode`:
1. Name: `mode`
2. Type: `enum`
3. Enum Values:
```json
{
  "auto": "Автоматический",
  "manual": "Ручной",
  "off": "Выключен"
}
```

Затем создаем свойство `power`:
1. Name: `power`
2. Type: `int`
3. Validation Parameters:
   - Min: 0
   - Max: 2000
4. Advanced Validation - Dependencies:
```json
{
  "property": "mode",
  "value": "manual",
  "condition": "equals",
  "error_message": "Мощность можно изменять только в ручном режиме"
}
```

---

## Полезные советы

### 1. Step (Дискретность)
- ✅ Используйте для UI слайдеров и регуляторов
- ✅ Удобно для IoT устройств с фиксированными шагами
- 💡 Примеры: яркость (10), температура (0.5), громкость (5)

### 2. Allowed Values
- ✅ Альтернатива enum для числовых типов
- ✅ Удобно для ограниченного набора значений
- ⚠️ Не используйте вместе с enum_values (для enum используйте только enum_values)

### 3. Rate Limit
- ✅ Защита кнопок от дребезга (1-3 сек)
- ✅ Ограничение частоты датчиков (5-60 сек)
- ✅ Защита от нагрузки на систему
- 💡 Используйте bypass_rate_limit=True для системных операций

### 4. Depends On
- ✅ Обеспечивает логическую связность
- ✅ Предотвращает некорректные состояния
- ⚠️ Избегайте циклических зависимостей
- 💡 Используйте информативные error_message

---

## Совместимость

- ✅ Старые свойства без новых параметров продолжают работать как раньше
- ✅ Валидация не применяется при загрузке значений из БД
- ✅ Все параметры опциональны
- ✅ Можно комбинировать различные валидации

---

## Дополнительная информация

- **Полная документация:** `PARAMS_DOCUMENTATION.md`
- **Примеры кода:** `examples/advanced_validation_examples.py`
- **Тесты:** `tests/test_advanced_validation.py`
- **Резюме:** `docs/ADVANCED_VALIDATION_SUMMARY.md`
