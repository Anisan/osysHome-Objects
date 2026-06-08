# Objects Module — User Guide

The **Objects** module is the central runtime database editor for osysHome. It manages the entire object-oriented data model of the system: classes, objects, properties, methods, schedules, and permissions.

---

## What Is the Objects Module?

The Objects module provides a visual interface to:

- Define **Classes** — reusable blueprints that describe what properties and methods a group of objects shares
- Create **Objects** — named instances that hold property values and can run methods
- Set **Property values** in real-time using WebSocket
- Execute **Methods** (Python scripts) and see the result immediately
- Schedule automated actions via cron or one-shot tasks
- Control **Permissions** per class or object
- **Export / Import** the entire data model as JSON

Other plugins (z2m, Tuya, MQTT, etc.) create and update objects automatically — the Objects module lets you inspect and edit them.

---

## Interface Overview

Navigate to **Admin → Objects** to open the main list.

### Toolbar

| Button | Action |
|---|---|
| **Add class** | Opens an inline dialog to create a new class |
| **Add object** | Opens an inline dialog to create a standalone object |
| **Permissions (global)** | Opens the global permission editor |
| **Settings** | Toggle "Show ID in lists" and "Render templates in list" |
| **Compact view** | Reduces visual density of the tree and hides secondary text/previews |
| **Expand all** | Expands the loaded class tree |
| **Collapse all** | Collapses all currently visible branches |
| **Export all** | Download the entire class/object tree as JSON |
| **Import from file** | Upload a JSON file to restore or extend the data model |
| Filter input | Live search across class/object names and descriptions |

The toolbar is sticky, so search and tree actions remain available while scrolling.

### Class Tree

Classes are shown as a collapsible accordion. Each card displays:

- Class name and description
- Count of child classes and objects
- A primary **Edit** button
- A **More actions** dropdown for Properties, Methods, Objects, Template, Permissions, and Delete

Tree branches are loaded lazily when expanded, which keeps the initial page load fast even for large object models.

Click the class name/row to expand or collapse. The collapsed/expanded state is saved in `localStorage`.

### Standalone Objects

Objects not attached to any class are listed in a separate **Standalone objects** section below the class tree.

Each object card shows:

- Object name and optional description
- Optional preview template (if enabled in settings)
- A primary **Edit** button
- A **More actions** dropdown for Properties, Methods, Template, Structure, Schedules, Permissions, and Delete

---

## Classes

### Creating a Class

1. Click **Add class** in the toolbar.
2. Fill in:
   - **Name** — unique identifier, no spaces or dots (e.g. `Sensor`, `Light`)
   - **Description** — optional human-readable label
   - **Parent class** — select to inherit properties and methods
3. Click **Save**.

### Editing a Class

Click the **pencil** icon in the class card, or navigate to `Objects?view=class&class=<id>`. The class page has tabs:

- **General** — name, description, parent class
- **Properties** — list of own properties and inherited (parent) properties
- **Methods** — list of own methods and inherited methods
- **Objects** — all objects that belong to this class
- **Template** — Jinja2 HTML template for rendering objects on the Dashboard
- **Permissions** — access control (separate page)
- **Tools** — bulk operations, maintenance, and export (see [Tools Tab](#tools-tab))

The class page also shows a compact summary block with:

Tab switching (General, Properties, Methods, etc.) uses Bootstrap and does **not** reload the page. The Tools tab works the same way.

- Class ID
- Total properties count (own + inherited)
- Total methods count (own + inherited)
- Number of objects assigned to this class

The `+` buttons for adding properties, methods, and objects are visually attached to their corresponding tabs.

### Deleting a Class

Click **Delete** in the class card (only shown if the class has no child classes and no objects). Or use the delete button on the class detail page.

---

## Objects

### Creating an Object

1. Click **Add object** in the toolbar (or click the **+** button inside a class card to pre-assign the class).
2. Fill in:
   - **Name** — unique identifier, no spaces or dots (e.g. `BedroomSensor`, `KitchenLight`)
   - **Description** — optional label
   - **Class** — select the class blueprint (optional for standalone objects)
3. Click **Save**. You are redirected to the object detail page to add properties.

### Object Detail Page (Tabs)

Navigate to `Objects?view=object&object=<id>` to open an object. The page has:

#### General Tab

Edit the object name, description, and class assignment.

At the top of the object page you will also see a compact summary block with:

- Object ID
- Property count
- Method count
- Schedule count
- Assigned class

#### Properties Tab

Lists all properties of the object, including inherited ones from its class. Each row shows:

- Property name (`ObjectName.propertyName`)
- Description, linked properties, method association, scheduled tasks
- Current **value** — updated live via WebSocket
- **Edit value** button (pencil icon) — opens the value editor modal

**Value Editor Modal** supports 7 types:

| Type | Editor |
|---|---|
| `int` | Number input with min/max/step hints |
| `float` | Decimal input with step/decimals hints |
| `str` | Text area, or select if `allowed_values` defined |
| `bool` | Toggle switch (True / False) |
| `datetime` | Datetime-local picker |
| `enum` | Dropdown with labels from `enum_values` |
| `dict` / `list` | JSON textarea |

Changes are sent immediately via WebSocket — no page reload needed.

Property action buttons:

- **Edit** — navigate to the property form to change type/validation
- **Add task** — add a scheduled task for this property
- **Delete** — remove the property
- **Redefine** — for inherited properties: create an object-level override

#### Methods Tab

Lists all methods. Each row shows the last execution time, source, and result. Buttons:

- **Run** — execute the method immediately; result appears inline
- **Edit / Delete** — for object-level methods
- **Redefine** — for inherited class methods
- **Add task** — schedule periodic execution

#### Template Tab

Edit the Jinja2 HTML template used to render this object as a widget on the Dashboard. Parent class templates are shown below for reference.

#### Structure Tab

Shows the full object structure (properties, methods, parents, permissions) with live WebSocket value updates.

#### Schedules Tab

Lists all scheduled tasks associated with this object. You can:

- **Enable / Disable** — toggle without a page reload
- **Edit** — navigate to the schedule edit form
- **Delete** — remove the task immediately

#### Permissions Tab

Opens a separate page (`?tab=permissions`) to configure read/write/execute access per user group.

#### Tools Tab

Grouped cards for maintenance and bulk actions:

**Maintenance**

| Tool | Description |
|---|---|
| Reload runtime | Reload this object from the database into runtime without server restart |
| Clear property history | Delete history records for one property or for all properties |
| Clear all links | Reset the `linked` field on all property values |
| Delete all schedules | Remove all cron tasks associated with this object |

**Copy and export**

| Tool | Description |
|---|---|
| Clone object | Create a copy with object-level properties, methods, and values; optional custom name and description copy |
| Export object | Download full object definition (`GET /api/export/object/<id>`) |
| Export values | Download a JSON snapshot of current values only |

---

## Tools Tab

The **Tools** tab is available on both class and object detail pages. Actions are grouped into cards with confirmation dialogs for destructive operations.

### Class Tools

Navigate to `Objects?view=class&class=<id>` and open the **Tools** tab.

Class tools operate on objects of this class **and all descendant classes** (child classes down the tree). The object count on tool cards includes this full scope. **Bulk create** is the exception: new objects are always assigned to the current class only.

#### Objects management

- **Bulk create objects** — create up to 100 objects in **this class** with a name pattern: `prefix` + `separator` + index (e.g. `Device_1` … `Device_10`). Existing names are skipped.
- **Bulk delete objects** — permanently delete all objects of this class and descendant classes (database + runtime).

#### Bulk values and methods

- **Run method on all objects** — executes the selected class method on every object sequentially. A modal shows per-object results (success, return value, or error).
- **Set property on all objects** — sets the same value on a property for every object via WebSocket (`setProperty`). Supports inherited properties. For `bool` use `1`/`0` or `true`/`false`; for `dict`/`list` use valid JSON.

#### Maintenance

- **Reload class in runtime** — reloads objects of this class and descendant classes from the database into runtime (`reload_objects_by_class`). Use after direct DB edits or plugin changes.
- **Clear property history** — deletes all `History` rows for the selected property across every object of the class (only properties with history enabled are listed).

#### Export

- **Export class** — download class definition as JSON. Options: **Include objects** (with values), **Include children** (child classes).

### Object Tools

Navigate to `Objects?view=object&object=<id>` and open the **Tools** tab (card layout described in the [Object detail page](#object-detail-page-tabs) section above).

### Tools API

Programmatic access (requires write permission on the class/object):

**Class tools** — `Objects?view=class_tool&class=<id>&op=<operation>`

| `op` | Method | Body (JSON) | Response |
|---|---|---|---|
| `reload` | GET or POST | — | `{ success, message }` |
| `bulk_create` | POST | `prefix`, `separator`, `start`, `count`, `description` | `{ created[], skipped[], created_count }` |
| `bulk_delete` | POST | — | `{ deleted[], deleted_count }` |
| `clear_history` | POST | `property` (name) | `{ deleted_count, property }` |
| `bulk_call_method` | POST | `method` (name) | `{ results[], ok_count, error_count }` |

**Object tools** — `Objects?view=object_tool&object=<id>&op=<operation>`

| `op` | Method | Body (JSON) | Response |
|---|---|---|---|
| `reload` | GET or POST | — | `{ success, message }` |
| `export_values` | GET | — | JSON file download |
| `clear_history` | POST | `property` (optional; empty = all) | `{ deleted_count, property }` |
| `clear_links` | POST | — | `{ cleared_count }` |
| `clear_schedules` | POST | — | `{ deleted_count, jobs[] }` |
| `clone` | POST | `name` (optional), `copy_description` (bool) | `{ object_id, object_name }` |

### Reload: Tools vs Legacy Endpoint

| Mechanism | URL | Effect |
|---|---|---|
| Legacy cache eviction | `Objects?view=reload&type=class&id=<id>` | Removes runtime objects (`remove_objects_by_class`) |
| Legacy cache eviction | `Objects?view=reload&type=object&id=<id>` | Removes one object from cache (`remove_object`) |
| Tools reload (class) | `class_tool&op=reload` | Reloads this class and descendant classes (`reload_objects_by_class`) |
| Tools reload (object) | `object_tool&op=reload` | Reloads one object from DB into runtime (`reload_object`) |

---

## Properties

### Adding a Property

Navigate to an object or class, go to the **Properties** tab, and click **+**. Or use `Objects?view=property&object=<id>` / `Objects?view=property&class=<id>`.

Fill in:

| Field | Description |
|---|---|
| **Name** | No spaces or dots. E.g. `temperature`, `is_on` |
| **Description** | Optional human-readable label |
| **Method** | Link to a method that computes this property's value |
| **History (days)** | How many days to keep change history (0 = disabled) |
| **Type** | `bool`, `int`, `float`, `str`, `datetime`, `dict`, `list`, `enum` |
| **Icon** | FontAwesome class (`fas fa-thermometer`) or Iconify (`mdi:thermometer`) |
| **Color** | Accent color for the property row |
| **Sort Order** | Display order (lower = first) |
| **Default Value** | Shown when no value is set |
| **Read Only** | Prevents editing from the UI |

**Type-specific validation:**

- `int`/`float`: min, max, step
- `float`: decimals (number of decimal places)
- `str`: regexp pattern
- `enum`: JSON dict mapping keys to display labels (`{"0": "Off", "1": "On"}`)

**Advanced validation:**

- **Allowed Values** — JSON array restricting valid values (`[1, 5, 10, 20]`)
- **Rate Limit** — minimum seconds between changes
- **Dependencies** — conditional validation based on another property's value

---

## Methods

### Adding a Method

Go to an object or class → **Methods** tab → **+**. Or `Objects?view=method&object=<id>`.

| Field | Description |
|---|---|
| **Name** | Method identifier, no spaces or dots |
| **Description** | Optional |
| **Code** | Python code (executed in the osysHome runtime) |
| **Call parent** | Whether to call the parent class method before/after/never |
| **Periodic** | Enable cron scheduling directly from the method form |

The code is written in the embedded Monaco/Ace editor. Saving is **async** — no page reload; success/error shown inline.

Click **Run** on the method form or in the Methods tab to execute immediately.

---

## Schedules

Schedules are task entries (`crontab` or one-shot `runtime`) linked to objects.

From `Objects?view=schedule&object=<id>&property=<pid>&op=add`:

| Field | Description |
|---|---|
| **Name** | Auto-generated, editable |
| **Code** | Python expression (e.g. `setProperty("Obj.prop", 1)`) |
| **Crontab** | Cron expression for periodic execution (e.g. `*/5 * * * *`) |
| **Runtime** | One-shot execution datetime |
| **Active** | Enable/disable without deleting |

---

## Permissions

The Permissions tab (per class or per object) controls access:

- **Read** — who can read property values
- **Write** — who can set property values
- **Execute** — who can call methods

Global permissions: `Objects?view=permissions`

---

## Import / Export

### Export

- **Export all** — full dump: `GET /api/export/all`
- **Export class** — single class with optional objects and children
- **Export object** — single object with properties and values

### Import

Click **Import from file** in the toolbar:

1. Select a `.json` file
2. Choose:
   - **Add classes** — import class definitions
   - **Add objects** — import object data
   - **Rewrite** — overwrite existing classes/objects with the same name
3. Click **Upload**

---

## Live Updates via WebSocket

The Objects module is connected to the osysHome WebSocket server. When any plugin calls `setProperty("Object.property", value)`, the new value appears **instantly** in the Properties tab — no refresh needed.

The value editor modal also uses WebSocket to deliver the new value and handles backend validation errors inline.

---

## Tips

- **Naming convention**: Use `PascalCase` for classes (`SensorClass`) and `CamelCase` or `snake_case` for objects (`BedroomSensor`, `kitchen_sensor`).
- **Templates**: Use the Jinja2 template system to render property values as HTML widgets for the Dashboard.
- **Inheritance**: Put shared properties/methods on the class. All objects of that class automatically have them.
- **Read-only properties**: Mark properties as `read_only` to prevent accidental edits from the UI (they can still be updated by plugins via `setProperty`).
- **Large trees**: Use the filter first, then `Expand all` only when you really need to inspect the entire hierarchy at once.
