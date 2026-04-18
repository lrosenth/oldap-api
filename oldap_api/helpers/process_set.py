from enum import Enum
from typing import Callable

from oldaplib.src.enums.attributeclass import AttributeClass
from oldaplib.src.helpers.observable_set import ObservableSet
from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.model import Model
from oldaplib.src.xsd.iri import Iri


def process_set(obj: Model,
                attr: AttributeClass,
                newval: set | list | dict | None,
                notifier: Callable[[Enum | Iri], None] = None):
    if newval != "NotSent":
        if isinstance(newval, (set, list)):
            if not newval:
                raise OldapErrorValue(f"Using an empty list is not allowed in the modify")
            if None in newval:
                raise OldapErrorValue(f"Using a None in a modify LangString is not allowed")
            if isinstance(attr.datatype, tuple):
                if attr.datatype[0] == ObservableSet:
                    if not all(isinstance(item, attr.datatype[1]) for item in newval):
                        tmp = ObservableSet({attr.datatype[1](x, validate=True) for x in newval},
                                            notifier=notifier, notify_data=attr.value)
                    else:
                        tmp = newval
                    if not isinstance(tmp, ObservableSet):
                        tmp = ObservableSet(tmp, notifier=notifier, notify_data=attr.value)
                    obj[attr] = tmp
                else:
                    raise OldapErrorValue(f"Expected an ObservableSet as datatype")
            else:
                obj[attr] = ObservableSet(newval, notifier=notifier, notify_data=attr.value)
        elif isinstance(newval, dict):
            if not newval:
                raise OldapErrorValue(f"Using an empty dict is not allowed in the modify")
            if not set(newval.keys()).issubset({"add", "del"}):
                raise OldapErrorValue(f"The sent command (keyword in dict) is not known")
            if "del" in newval:
                deleting = newval["del"]
                if not isinstance(deleting, list):
                    raise OldapErrorValue("The given attributes in add and del must be in a list")
                if not deleting:
                    raise OldapErrorValue(f"Using an empty list is not allowed in the modify")
                if isinstance(attr.datatype, tuple):
                    if attr.datatype[0] == ObservableSet:
                        if not all(isinstance(item, attr.datatype[1]) for item in deleting):
                            deleting = {attr.datatype[1](x, validate=True) for x in deleting}
                for item in deleting:
                    obj[attr].discard(item)
            if "add" in newval:
                adding = newval["add"]
                if not isinstance(adding, list):
                    raise OldapErrorValue("The given attributes in add and del must be in a list")
                if not adding:
                    raise OldapErrorValue(f"Using an empty list is not allowed in the modify")
                if isinstance(attr.datatype, tuple):
                    if attr.datatype[0] == ObservableSet:
                        if not all(isinstance(item, attr.datatype[1]) for item in adding):
                            deleting = {attr.datatype[1](x, validate=True) for x in adding}
                for item in adding:
                    obj[attr].add(item)
        elif newval is None:
            del obj[attr]
            if hasattr(obj, 'notify'):
                obj.notify()
        else:
            raise OldapErrorValue(f"Either a List or a dict is required.")
