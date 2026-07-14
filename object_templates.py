from app.core.lib.object import getObject


def attach_object_templates(objects, render_templates=False):
    hydrated_objects = []
    for obj in objects:
        obj_dict = obj.copy()
        if render_templates:
            runtime_object = getObject(obj_dict["name"])
            if runtime_object and runtime_object.has_render_template():
                obj_dict["template"] = runtime_object.render()
            else:
                obj_dict["template"] = ""
        else:
            obj_dict["template"] = ""
        hydrated_objects.append(obj_dict)
    return hydrated_objects
