# Objects - Object Management Module

![Objects Icon](static/objects.png)

A comprehensive object-oriented management system for creating, editing, and managing classes, objects, properties, and methods with advanced validation capabilities.

## Description

The `Objects` module provides a full-featured object management system for the osysHome platform. It enables you to create hierarchical class structures, instantiate objects from classes, define properties with advanced validation rules, create methods, and manage object lifecycles through scheduling and permissions.

## Main Features

- ✅ **Class Management**: Create hierarchical class structures with inheritance
- ✅ **Object Management**: Create and manage object instances from classes
- ✅ **Property Management**: Define properties with advanced validation:
  - Type validation (int, float, str, bool, enum, etc.)
  - Range validation (min/max)
  - Step validation (discreteness)
  - Allowed values
  - Rate limiting
  - Dependencies between properties
  - Regular expressions
- ✅ **Method Management**: Define and execute methods on objects and classes
- ✅ **Scheduling**: Schedule object operations and method calls
- ✅ **Permissions**: Manage access control for objects and classes
- ✅ **Admin Tools**: Bulk operations and maintenance on the class/object **Tools** tab (create/delete objects, run methods, set properties, reload runtime, clear history, clone, export)
- ✅ **Search Integration**: Full-text search across classes, objects, properties, methods, and values
- ✅ **Widget Support**: Dashboard widget showing object statistics
- ✅ **Template Rendering**: Customizable object templates

## Module Structure

### Classes
Classes define the structure and behavior for objects. They support:
- Hierarchical inheritance (parent-child relationships)
- Properties definition
- Methods definition
- Description and metadata

### Objects
Objects are instances of classes (or standalone objects). They have:
- Properties with values
- Methods that can be executed
- Templates for rendering
- Scheduling capabilities
- Permissions

### Properties
Properties define attributes of objects and classes:
- **Types**: int, float, str, bool, enum, date, time, datetime, etc.
- **Validation**: min, max, step, allowed_values, regexp
- **Advanced Features**: rate_limit, depends_on
- **Metadata**: icon, color, description

### Methods
Methods define actions that can be performed on objects:
- Code execution
- Parameters support
- Scheduling
- Permissions

## Admin Panel

The module provides a comprehensive admin interface accessible through the main admin panel:

### Main View
- **Classes Tree**: Hierarchical view of all classes
- **Standalone Objects**: Objects not belonging to any class
- **Settings**: Module configuration options

### Class Management (`view=class`)
- Create, edit, and delete classes
- Manage class hierarchy
- Define class properties and methods
- View class information

### Object Management (`view=object`)
- Create, edit, and delete objects
- Assign objects to classes
- Manage object properties and values
- Define object methods
- Configure templates
- Schedule operations

### Property Management (`view=property`)
- Create and edit properties
- Configure validation rules
- Set up dependencies
- Define metadata (icon, color)

### Method Management (`view=method`)
- Create and edit methods
- Write method code
- Configure parameters
- Set permissions

### Scheduling (`view=schedule`)
- Schedule object operations
- Configure recurring tasks
- Manage scheduled jobs

### Permissions (`view=permissions`)
- Manage access control
- Configure user permissions
- Set object-level permissions

### Tools Tab (class and object pages)

The **Tools** tab on the class and object detail pages groups maintenance and bulk actions into cards. Tabs switch without a page reload (Bootstrap), except when navigating from the separate Permissions page.

**Important:** Class tools affect objects of this class **and all descendant classes** down the inheritance tree. Exception: **bulk create** always adds new objects only to the current class.

**Class tools** (`view=class&class=<id>` → Tools tab):

| Group | Action |
|---|---|
| Objects management | Bulk create objects (prefix, separator, index, count up to 100), bulk delete all class objects |
| Bulk values and methods | Run a method on every object (results summary dialog), set a property value on all objects via WebSocket |
| Maintenance | Reload all class objects in runtime from DB, clear property change history for all class objects |
| Export | Export class JSON (optional objects and child classes) |

**Object tools** (`view=object&object=<id>` → Tools tab):

| Group | Action |
|---|---|
| Maintenance | Reload object in runtime, clear property history (one property or all), clear all `linked` fields, delete all schedules |
| Copy and export | Clone object (optional name, copy description), export object JSON, export values JSON |

Server API handlers: `class_tools.py`, `object_tools.py` (`view=class_tool`, `view=object_tool`). See [docs/objects.md](docs/objects.md) for request parameters.

## Advanced Validation

The module supports advanced validation features for properties. See [VALIDATION_GUIDE.md](VALIDATION_GUIDE.md) for detailed documentation.

### Validation Types

1. **Step (Discreteness)**: For int and float types, defines the step size for value changes
2. **Allowed Values**: Restricts property values to a specific list
3. **Rate Limit**: Prevents property changes more frequently than specified interval
4. **Depends On**: Defines dependencies on other property values

### Example: Smart Thermostat

```json
{
  "type": "float",
  "params": {
    "min": 18.0,
    "max": 30.0,
    "step": 0.5,
    "decimals": 1,
    "rate_limit": 10.0,
    "depends_on": {
      "property": "enabled",
      "value": true,
      "condition": "equals"
    }
  }
}
```

## Usage

### Accessing the Module

Navigate to the admin panel and select the "Objects" module from the System category.

### Creating a Class

1. Click "Add Class" or select an existing class
2. Enter class name and description
3. Optionally select a parent class for inheritance
4. Save the class

### Creating an Object

1. Click "Add Object" or select a class to create an object from
2. Enter object name and description
3. Optionally select a class
4. Configure template if needed
5. Save the object

### Adding Properties

1. Navigate to the object or class
2. Go to the "Properties" tab
3. Click "Add Property"
4. Configure:
   - Name and type
   - Validation parameters (min, max, step, etc.)
   - Advanced validation (allowed_values, rate_limit, depends_on)
   - Metadata (icon, color)
5. Save the property

### Adding Methods

1. Navigate to the object or class
2. Go to the "Methods" tab
3. Click "Add Method"
4. Enter method name and code
5. Configure parameters and permissions
6. Save the method

## Search Integration

The module provides search functionality that indexes:
- Classes (by name and description)
- Objects (by name and description)
- Properties (by name and description)
- Methods (by name, description, and code)
- Values (by value content)

Search results include direct links to the relevant items.

## Widget

The module provides a dashboard widget showing:
- Total number of classes
- Total number of objects
- Total number of property values

## Configuration

Module settings available in the admin panel:

- **Render Templates**: Enable/disable template rendering in the object list
- **Show ID**: Display object/class IDs in the interface

## Reload Functionality

Two reload mechanisms exist:

| Endpoint | Behavior |
|---|---|
| `Objects?view=reload&type=class&id={class_id}` | Removes cached runtime objects of the class (`remove_objects_by_class`) |
| `Objects?view=reload&type=object&id={object_id}` | Removes a single object from runtime cache (`remove_object`) |
| **Tools → Reload runtime** (`view=class_tool&op=reload` / `view=object_tool&op=reload`) | Reloads from DB into runtime. Class tool reloads this class and descendant classes (`reload_objects_by_class`); object tool reloads one object |

## Technical Details

- **Database Models**: Class, Object, Property, Method, Value, History
- **Storage**: Integrated with ObjectsStorage for runtime object management
- **Tool routes**: `plugins/Objects/class_tools.py`, `plugins/Objects/object_tools.py`
- **Permissions**: Role-based access control (admin/root see all, others see non-system items)
- **Templates**: Jinja2 template support for object rendering

## Version

Current version: **1.0**

## Category

System

## Actions

The module provides the following actions:
- `search` - Full-text search across objects, classes, properties, methods, and values
- `widget` - Dashboard widget with object statistics

## Requirements

- Flask
- Flask-Login (for authentication)
- SQLAlchemy
- WTForms
- osysHome core system

## Author

Eraser

## License

See the main osysHome project license

## Related Documentation

- [docs/objects.md](docs/objects.md) - Full user guide (interface, tabs, tools API)
- [docs/object-model.md](docs/object-model.md) - Object model, inheritance, runtime API
- [VALIDATION_GUIDE.md](docs/VALIDATION_GUIDE.md) - Detailed guide on advanced property validation

